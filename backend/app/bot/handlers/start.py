from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards import main_menu, open_app
from app.db.models import Lobby, User

INVITE_PREFIX = "join_"  # t.me/<бот>?start=join_<код> — приглашение в закрытую пати


async def start(
    message: Message, user: User, webapp_url: str | None, session: AsyncSession, command: CommandObject
) -> None:
    if command.args and command.args.startswith(INVITE_PREFIX) and webapp_url:
        await invite(message, session, webapp_url, command.args.removeprefix(INVITE_PREFIX))
        return
    if user.is_onboarded:
        text = texts.welcome_back(user.first_name)
    else:
        text = texts.welcome_new(user.first_name)
    hint = texts.OPEN_APP_HINT if webapp_url else texts.APP_NOT_READY
    await message.answer(f"{text}\n\n{hint}", reply_markup=main_menu(webapp_url))


async def invite(message: Message, session: AsyncSession, webapp_url: str, code: str) -> None:
    """Кнопка, которая откроет закрытую пати в приложении. Пускать или нет (возраст, блокировки) решает API."""
    title = await session.scalar(select(Lobby.title).where(Lobby.invite_code == code))
    if title is None:
        await message.answer(texts.INVITE_EXPIRED)
        return
    keyboard = open_app(webapp_url, f"invite/{code}", texts.BUTTON_OPEN_LOBBY)
    await message.answer(texts.invite_open(title), reply_markup=keyboard)


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(start, CommandStart())
    return router
