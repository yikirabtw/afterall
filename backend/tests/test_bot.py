"""Бот целиком: апдейт проходит через диспетчер, мидлвари и хендлеры; вместо сети — запись запросов."""

from datetime import datetime, timedelta, timezone

import pytest
from aiogram import Bot
from aiogram.methods import AnswerCallbackQuery, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TelegramUser
from fakes import RecordingSession
from sqlalchemy import select

from app.bot import texts
from app.bot.dispatcher import build_dispatcher
from app.bot.keyboards import HELP_CALLBACK
from app.db.models import User
from app.services.users import is_ban_active

WEBAPP_URL = "https://example.com"
USER_ID = 100


@pytest.fixture
def bot() -> Bot:
    return Bot("42:TEST", session=RecordingSession())


def sent(bot: Bot, method_type: type) -> list:
    return [request for request in bot.session.requests if isinstance(request, method_type)]


def telegram_user(first_name: str = "Аня") -> TelegramUser:
    return TelegramUser(id=USER_ID, is_bot=False, first_name=first_name, username="anya", language_code="ru")


def message_update(text: str, first_name: str = "Аня") -> Update:
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=USER_ID, type="private"),
            from_user=telegram_user(first_name),
            text=text,
        ),
    )


def callback_update(data: str) -> Update:
    return Update(
        update_id=2,
        callback_query=CallbackQuery(
            id="1",
            from_user=telegram_user(),
            chat_instance="1",
            data=data,
            message=Message(
                message_id=1, date=datetime.now(timezone.utc), chat=Chat(id=USER_ID, type="private"), text="меню"
            ),
        ),
    )


async def load_users(session_maker) -> list[User]:
    async with session_maker() as session:
        return list(await session.scalars(select(User)))


async def test_start_registers_new_user(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("/start"))

    [user] = await load_users(session_maker)
    assert (user.telegram_id, user.first_name, user.username) == (USER_ID, "Аня", "anya")
    assert user.last_seen_at is not None

    [reply] = sent(bot, SendMessage)
    assert reply.text.startswith("Привет, Аня!")
    assert texts.OPEN_APP_HINT in reply.text
    assert reply.reply_markup.inline_keyboard[0][0].web_app.url == WEBAPP_URL


async def test_start_without_webapp_has_no_app_button(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, webapp_url=None)

    await dispatcher.feed_update(bot, message_update("/start"))

    [reply] = sent(bot, SendMessage)
    assert texts.APP_NOT_READY in reply.text
    buttons = [button for row in reply.reply_markup.inline_keyboard for button in row]
    assert all(button.web_app is None for button in buttons)


async def test_name_is_escaped(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("/start", first_name="<b>Аня</b>"))

    [reply] = sent(bot, SendMessage)
    assert "&lt;b&gt;Аня&lt;/b&gt;" in reply.text


async def test_repeated_start_updates_same_user(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)
    await dispatcher.feed_update(bot, message_update("/start"))
    async with session_maker.begin() as session:
        user = await session.scalar(select(User))
        user.onboarded_at = datetime.now(timezone.utc)

    await dispatcher.feed_update(bot, message_update("/start", first_name="Анна"))

    [user] = await load_users(session_maker)
    assert user.first_name == "Анна"
    assert sent(bot, SendMessage)[-1].text.startswith("С возвращением, Анна!")


async def test_help_command(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("/help"))

    assert [reply.text for reply in sent(bot, SendMessage)] == [texts.HELP]


async def test_help_button(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, callback_update(HELP_CALLBACK))

    assert [reply.text for reply in sent(bot, SendMessage)] == [texts.HELP]
    assert len(sent(bot, AnswerCallbackQuery)) == 1  # кнопка перестаёт «крутиться»


async def test_unknown_text_gets_fallback(bot, session_maker):
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("привет"))

    assert [reply.text for reply in sent(bot, SendMessage)] == [texts.FALLBACK]


async def test_banned_user_is_stopped(bot, session_maker):
    async with session_maker.begin() as session:
        session.add(User(telegram_id=USER_ID, first_name="Аня", is_banned=True))
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("/start"))

    assert [reply.text for reply in sent(bot, SendMessage)] == [texts.BANNED]


async def test_expired_ban_lets_user_in(bot, session_maker):
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    async with session_maker.begin() as session:
        session.add(User(telegram_id=USER_ID, first_name="Аня", is_banned=True, banned_until=yesterday))
    dispatcher = build_dispatcher(session_maker, WEBAPP_URL)

    await dispatcher.feed_update(bot, message_update("/start"))

    [reply] = sent(bot, SendMessage)
    assert reply.text.startswith("Привет, Аня!")


@pytest.mark.parametrize(
    ("is_banned", "banned_until", "expected"),
    [
        (False, None, False),
        (True, None, True),  # навсегда
        (True, datetime(2026, 6, 2, tzinfo=timezone.utc), True),
        (True, datetime(2026, 5, 31, tzinfo=timezone.utc), False),
        (True, datetime(2026, 6, 2), True),  # так время возвращает SQLite — без часового пояса
    ],
)
def test_is_ban_active(is_banned, banned_until, expected):
    user = User(telegram_id=1, first_name="x", is_banned=is_banned, banned_until=banned_until)
    assert is_ban_active(user, now=datetime(2026, 6, 1, tzinfo=timezone.utc)) is expected
