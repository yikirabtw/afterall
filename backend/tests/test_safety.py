"""Блокировки, жалобы и их разбор модераторами в боте."""

from datetime import datetime, timedelta, timezone

import pytest
from aiogram import Bot
from aiogram.methods import AnswerCallbackQuery, EditMessageText
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TelegramUser
from conftest import ADMIN_TELEGRAM_ID
from fakes import RecordingSession, outbox
from players import Player
from sqlalchemy import select, update

import app.api.routes.safety as safety_routes
from app.bot import texts
from app.bot.dispatcher import build_dispatcher
from app.db.enums import ReportReason, ReportStatus, UserRole
from app.db.models import Report, User
from app.domain.time import as_utc, utcnow


async def match(client, a: Player, b: Player) -> None:
    for x, y in ((a, b), (b, a)):
        response = await client.post(f"/api/people/{y.id}/react", json={"kind": "like"}, headers=x.headers)
        assert response.status_code == 200, response.text


async def report(client, me: Player, target: Player, expect: int = 204, **fields) -> dict | None:
    body = {"user_id": target.id, "reason": "toxic", **fields}
    response = await client.post("/api/reports", json=body, headers=me.headers)
    assert response.status_code == expect, response.text
    return response.json() if response.content else None


async def matches(client, player: Player) -> list[int]:
    return [m["user_id"] for m in (await client.get("/api/matches", headers=player.headers)).json()]


# --- Блокировки ---


async def test_block_hides_both_ways_and_unblock_restores(client, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)

    assert (await client.post(f"/api/blocks/{other.id}", headers=me.headers)).status_code == 204

    assert await matches(client, me) == [] and await matches(client, other) == []
    [blocked] = (await client.get("/api/blocks", headers=me.headers)).json()
    assert (blocked["user_id"], blocked["display_name"]) == (other.id, "Игрок 2")
    assert (await client.get("/api/blocks", headers=other.headers)).json() == []  # кто заблокировал — не видно

    assert (await client.delete(f"/api/blocks/{other.id}", headers=me.headers)).status_code == 204
    assert await matches(client, me) == [other.id]


async def test_block_validation(client, make_player):
    me = await make_player()
    response = await client.post(f"/api/blocks/{me.id}", headers=me.headers)
    assert (response.status_code, response.json()["detail"]) == (422, "cannot_target_self")
    response = await client.post("/api/blocks/999999", headers=me.headers)
    assert (response.status_code, response.json()["detail"]) == (404, "user_not_found")


# --- Жалобы ---


async def test_report_blocks_and_goes_to_moderators(client, notifier, session_maker, make_player):
    me, other, moderator = await make_player(age=15), await make_player(age=17), await make_player()
    async with session_maker.begin() as session:
        await session.execute(update(User).where(User.id == moderator.id).values(role=UserRole.MODERATOR))
    await match(client, me, other)
    await client.post(f"/api/chats/direct/{other.id}/messages", json={"body": "привет"}, headers=me.headers)
    await client.post(f"/api/chats/direct/{me.id}/messages", json={"body": "скинь фото <3"}, headers=other.headers)
    notifier.bot.session.requests.clear()

    await report(client, me, other, reason="minor_safety", comment="просит фото")

    assert await matches(client, me) == []  # жалоба сразу блокирует
    cards = outbox(notifier)
    assert {card.chat_id for card in cards} == {ADMIN_TELEGRAM_ID, moderator.telegram_id}
    card = cards[0]
    assert "Угроза безопасности подростка" in card.text
    assert "Игрок 2, 17" in card.text and "Игрок 1, 15" in card.text  # на кого и от кого, с возрастом
    assert "просит фото" in card.text
    assert "скинь фото &lt;3" in card.text  # последние сообщения — модератору, экранированные
    async with session_maker() as session:
        saved = await session.scalar(select(Report))
    buttons = [button.callback_data for row in card.reply_markup.inline_keyboard for button in row]
    assert buttons == [f"mod:{saved.id}:ban7", f"mod:{saved.id}:ban", f"mod:{saved.id}:reject"]


async def test_report_needs_match_or_shared_lobby(client, world, make_player):
    me, stranger = await make_player(), await make_player()
    await report(client, me, stranger, expect=404)

    # В общей пати — можно, с её сообщениями
    lobby = (
        await client.post(
            "/api/lobbies",
            json={"kind": "game", "game_id": world["dota"], "title": "Катка", "slots_total": 5},
            headers=me.headers,
        )
    ).json()["id"]
    await client.post(f"/api/lobbies/{lobby}/apply", headers=stranger.headers)
    await client.post(f"/api/lobbies/{lobby}/members/{stranger.id}/accept", headers=me.headers)
    await report(client, me, stranger, lobby_id=lobby)


async def test_blocked_disappears_from_party_chat(client, world, make_player):
    owner, guest = await make_player(), await make_player()
    lobby = (
        await client.post(
            "/api/lobbies",
            json={"kind": "game", "game_id": world["dota"], "title": "Катка", "slots_total": 5},
            headers=owner.headers,
        )
    ).json()["id"]
    await client.post(f"/api/lobbies/{lobby}/apply", headers=guest.headers)
    await client.post(f"/api/lobbies/{lobby}/members/{guest.id}/accept", headers=owner.headers)
    await client.post(f"/api/chats/lobby/{lobby}/messages", json={"body": "привет всем"}, headers=owner.headers)
    await client.post(f"/api/chats/lobby/{lobby}/messages", json={"body": "гадость"}, headers=guest.headers)

    await report(client, owner, guest, lobby_id=lobby)

    chat = (await client.get(f"/api/chats/lobby/{lobby}", headers=owner.headers)).json()
    assert [m["body"] for m in chat["messages"]] == ["привет всем"]
    [summary] = (await client.get("/api/chats", headers=owner.headers)).json()
    assert summary["last_message"]["body"] == "привет всем"


async def test_repeat_report_does_not_spam_moderators(client, notifier, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)
    notifier.bot.session.requests.clear()

    await report(client, me, other)
    await report(client, me, other, reason="spam")

    assert len(outbox(notifier)) == 1  # один админ, одна карточка


async def test_report_limit(client, make_player, monkeypatch):
    monkeypatch.setattr(safety_routes, "REPORTS_PER_DAY", 1)
    me, first, second = await make_player(), await make_player(), await make_player()
    await match(client, me, first)
    await match(client, me, second)

    await report(client, me, first)
    await report(client, me, second, expect=429)


# --- Разбор в боте ---


def press(data: str, telegram_id: int) -> Update:
    return Update(
        update_id=1,
        callback_query=CallbackQuery(
            id="1",
            from_user=TelegramUser(id=telegram_id, is_bot=False, first_name="Модер"),
            chat_instance="1",
            data=data,
            message=Message(
                message_id=1,
                date=datetime.now(timezone.utc),
                chat=Chat(id=telegram_id, type="private"),
                text="Жалоба",
            ),
        ),
    )


@pytest.fixture
def bot() -> Bot:
    return Bot("42:TEST", session=RecordingSession())


async def reports_on(client, target: Player, *reporters: Player) -> list[int]:
    for reporter in reporters:
        await match(client, reporter, target)
        await report(client, reporter, target)
    async with client._transport.app.state.session_maker() as session:  # type: ignore[attr-defined]
        return list(await session.scalars(select(Report.id).order_by(Report.id)))


async def load(session_maker, model, id_):
    async with session_maker() as session:
        return await session.get(model, id_)


async def test_week_ban_closes_all_reports_on_that_person(client, bot, session_maker, make_player):
    target, a, b = await make_player(), await make_player(), await make_player()
    first, second = await reports_on(client, target, a, b)
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))

    await dispatcher.feed_update(bot, press(f"mod:{first}:ban7", ADMIN_TELEGRAM_ID))

    banned = await load(session_maker, User, target.id)
    assert banned.is_banned
    assert as_utc(banned.banned_until) - utcnow() > timedelta(days=6, hours=23)
    for report_id in (first, second):
        assert (await load(session_maker, Report, report_id)).status == ReportStatus.RESOLVED
    [edited] = [r for r in bot.session.requests if isinstance(r, EditMessageText)]
    assert "бан на 7 дней" in edited.text and edited.reply_markup is None
    # Забаненный пропал и из API
    response = await client.get("/api/me", headers=target.headers)
    assert (response.status_code, response.json()["detail"]) == (403, "banned")


async def test_only_moderators_can_decide(client, bot, session_maker, make_player):
    target, reporter = await make_player(), await make_player()
    [report_id] = await reports_on(client, target, reporter)
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))

    await dispatcher.feed_update(bot, press(f"mod:{report_id}:ban", 424242))

    [answer] = [r for r in bot.session.requests if isinstance(r, AnswerCallbackQuery)]
    assert answer.text == texts.MOD_NO_RIGHTS
    assert not (await load(session_maker, User, target.id)).is_banned
    assert (await load(session_maker, Report, report_id)).status == ReportStatus.OPEN


async def test_reject_and_second_press(client, bot, session_maker, make_player):
    target, reporter = await make_player(), await make_player()
    [report_id] = await reports_on(client, target, reporter)
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))

    await dispatcher.feed_update(bot, press(f"mod:{report_id}:reject", ADMIN_TELEGRAM_ID))
    assert (await load(session_maker, Report, report_id)).status == ReportStatus.REJECTED
    assert not (await load(session_maker, User, target.id)).is_banned

    # Второй модератор нажал позже — решение уже есть
    await dispatcher.feed_update(bot, press(f"mod:{report_id}:ban", ADMIN_TELEGRAM_ID))
    answers = [r for r in bot.session.requests if isinstance(r, AnswerCallbackQuery)]
    assert answers[-1].text == texts.MOD_ALREADY_DONE
    assert not (await load(session_maker, User, target.id)).is_banned


def test_reasons_have_labels():
    assert set(texts.REPORT_REASONS) == {reason.value for reason in ReportReason}
