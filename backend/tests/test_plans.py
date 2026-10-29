"""Тарифы: выдача админом в боте, тариф в профиле, значок у других."""

from datetime import datetime, timedelta, timezone

import pytest
from aiogram import Bot
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TelegramUser
from conftest import ADMIN_TELEGRAM_ID
from fakes import RecordingSession
from sqlalchemy import select, update

from app.bot import texts
from app.bot.dispatcher import build_dispatcher
from app.db.models import Subscription, User
from app.domain.time import utcnow
from app.services.plans import plan_of


@pytest.fixture
def bot() -> Bot:
    return Bot("42:TEST", session=RecordingSession())


def command(text: str, telegram_id: int = ADMIN_TELEGRAM_ID) -> Update:
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=telegram_id, type="private"),
            from_user=TelegramUser(id=telegram_id, is_bot=False, first_name="Админ", username="boss"),
            text=text,
        ),
    )


def replies(bot: Bot) -> list[SendMessage]:
    return [r for r in bot.session.requests if isinstance(r, SendMessage)]


async def plan(session_maker, user_id: int):
    async with session_maker() as session:
        return await plan_of(session, user_id, utcnow())


async def test_admin_grants_premium_to_self_and_to_others(bot, session_maker, make_player):
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))
    other = await make_player()

    await dispatcher.feed_update(bot, command("/premium"))
    await dispatcher.feed_update(bot, command(f"/plus @{other.username} 7"))

    async with session_maker() as session:
        admin_id = await session.scalar(select(User.id).where(User.telegram_id == ADMIN_TELEGRAM_ID))
    mine, until = await plan(session_maker, admin_id)
    assert mine == "premium" and until - utcnow() > timedelta(days=29)
    theirs, until = await plan(session_maker, other.id)
    assert theirs == "plus" and timedelta(days=6) < until - utcnow() <= timedelta(days=7)

    granted_self, granted_other, gift = replies(bot)
    assert "Premium" in granted_self.text and "Plus" in granted_other.text
    assert gift.chat_id == other.telegram_id and "Тебе выдан" in gift.text

    # Повторная выдача продлевает, /free — снимает
    await dispatcher.feed_update(bot, command(f"/plus {other.telegram_id} 10"))
    _, until = await plan(session_maker, other.id)
    assert until - utcnow() > timedelta(days=16)
    await dispatcher.feed_update(bot, command(f"/free @{other.username}"))
    assert (await plan(session_maker, other.id))[0] == "free"


async def test_not_admin_cannot_grant(bot, session_maker, make_player):
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))
    stranger = await make_player()

    await dispatcher.feed_update(bot, command("/premium", telegram_id=stranger.telegram_id))

    assert (await plan(session_maker, stranger.id))[0] == "free"
    assert replies(bot)[0].text == texts.FALLBACK


async def test_unknown_user(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))
    await dispatcher.feed_update(bot, command("/premium @nobody"))
    assert replies(bot)[0].text == texts.ADMIN_USER_NOT_FOUND


async def test_plan_in_profile_and_on_cards(client, make_player, set_plan, session_maker):
    me, other = await make_player(), await make_player()
    await set_plan("premium", user_id=other.id)

    mine = (await client.get("/api/me", headers=me.headers)).json()["plan"]
    assert mine == {"plan": "free", "until": None, "photos_max": 1, "active_lobbies_max": 2, "rewinds_per_day": 0}
    theirs = (await client.get("/api/me", headers=other.headers)).json()["plan"]
    assert (theirs["plan"], theirs["photos_max"], theirs["active_lobbies_max"]) == ("premium", 3, 10)

    [card] = (await client.get("/api/people", headers=me.headers)).json()
    assert card["plan"] == "premium"  # значок у ника

    # Подписка закончилась — тариф снова бесплатный
    async with session_maker.begin() as session:
        await session.execute(update(Subscription).values(ends_at=utcnow() - timedelta(minutes=1)))
    assert (await client.get("/api/me", headers=other.headers)).json()["plan"]["plan"] == "free"


# --- Кто лайкнул ---


async def likes(client, player) -> dict:
    response = await client.get("/api/people/likes", headers=player.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def like(client, a, b, kind: str = "like") -> dict:
    return (await client.post(f"/api/people/{b.id}/react", json={"kind": kind}, headers=a.headers)).json()


async def test_free_sees_only_how_many_liked(client, make_player):
    me, fan = await make_player(), await make_player()
    await like(client, fan, me)

    assert await likes(client, me) == {"count": 1, "people": None}  # ни имён, ни фото


async def test_subscribers_see_who_liked_newest_first(client, make_player, set_plan, session_maker):
    me, first, second, answered, skipped, blocked = [await make_player() for _ in range(6)]
    for fan in (first, second, answered, skipped, blocked):
        await like(client, fan, me)
    await like(client, me, answered)  # ответил — это уже мэтч, не «лайк мне»
    await like(client, me, skipped, "skip")
    await client.post(f"/api/blocks/{blocked.id}", headers=me.headers)
    await set_plan("plus", user_id=me.id)

    result = await likes(client, me)

    assert result["count"] == 2
    assert [p["user_id"] for p in result["people"]] == [second.id, first.id]
    assert result["people"][0]["compatibility"] > 0

    # Лайк в ответ из списка — сразу мэтч, и человек уходит из списка
    assert (await like(client, me, second))["match"]["user_id"] == second.id
    assert [p["user_id"] for p in (await likes(client, me))["people"]] == [first.id]


async def test_likes_respect_age_rules(client, make_player, set_plan):
    me = await make_player(age=25)
    teen = await make_player(age=16)
    adult = await make_player(age=19)
    await like(client, adult, me)
    await set_plan("premium", user_id=me.id)

    # 16-летний 25-летнего не видит и лайкнуть не может; лайк от 19-летнего — есть
    response = await client.post(f"/api/people/{me.id}/react", json={"kind": "like"}, headers=teen.headers)
    assert response.status_code == 404
    assert [p["user_id"] for p in (await likes(client, me))["people"]] == [adult.id]



# --- Вернуть пропущенную анкету ---


async def rewind(client, player, expect: int = 200) -> dict:
    response = await client.post("/api/people/rewind", headers=player.headers)
    assert response.status_code == expect, response.text
    return response.json()


async def test_free_cannot_rewind(client, make_player):
    me, other = await make_player(), await make_player()
    await like(client, me, other, "skip")

    assert (await rewind(client, me, expect=403))["detail"] == "rewind_needs_plan"


async def test_rewind_returns_last_skipped_to_feed(client, make_player, set_plan):
    me, first, second = await make_player(), await make_player(), await make_player()
    await set_plan("plus", user_id=me.id)
    await like(client, me, first, "skip")
    await like(client, me, second, "skip")
    assert (await client.get("/api/people", headers=me.headers)).json() == []

    result = await rewind(client, me)

    assert (result["person"]["user_id"], result["left"]) == (second.id, 2)
    assert [p["user_id"] for p in (await client.get("/api/people", headers=me.headers)).json()] == [second.id]
    assert (await rewind(client, me))["person"]["user_id"] == first.id


async def test_plus_has_three_rewinds_a_day_premium_unlimited(client, make_player, set_plan):
    me = await make_player()
    people = [await make_player() for _ in range(5)]
    for person in people:
        await like(client, me, person, "skip")
    await set_plan("plus", user_id=me.id)

    for left in (2, 1, 0):
        assert (await rewind(client, me))["left"] == left
    assert (await rewind(client, me, expect=429))["detail"] == "rewinds_limit"

    await set_plan("premium", user_id=me.id)
    assert (await rewind(client, me))["left"] is None


async def test_rewind_does_not_undo_likes_or_return_blocked(client, make_player, set_plan):
    me, liked, blocked = await make_player(), await make_player(), await make_player()
    await set_plan("premium", user_id=me.id)
    await like(client, me, liked)  # лайк не откатывается — он мог стать мэтчем
    await like(client, me, blocked, "skip")
    await client.post(f"/api/blocks/{blocked.id}", headers=me.headers)

    assert (await rewind(client, me, expect=404))["detail"] == "nothing_to_rewind"


async def test_plan_shows_rewinds_per_day(client, make_player, set_plan):
    me = await make_player()
    assert (await client.get("/api/me", headers=me.headers)).json()["plan"]["rewinds_per_day"] == 0
    await set_plan("plus", user_id=me.id)
    assert (await client.get("/api/me", headers=me.headers)).json()["plan"]["rewinds_per_day"] == 3
    await set_plan("premium", user_id=me.id)
    assert (await client.get("/api/me", headers=me.headers)).json()["plan"]["rewinds_per_day"] is None
