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
    assert mine == {"plan": "free", "until": None, "photos_max": 1, "active_lobbies_max": 2}
    theirs = (await client.get("/api/me", headers=other.headers)).json()["plan"]
    assert (theirs["plan"], theirs["photos_max"], theirs["active_lobbies_max"]) == ("premium", 3, 10)

    [card] = (await client.get("/api/people", headers=me.headers)).json()
    assert card["plan"] == "premium"  # значок у ника

    # Подписка закончилась — тариф снова бесплатный
    async with session_maker.begin() as session:
        await session.execute(update(Subscription).values(ends_at=utcnow() - timedelta(minutes=1)))
    assert (await client.get("/api/me", headers=other.headers)).json()["plan"]["plan"] == "free"
