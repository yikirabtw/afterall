from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot import texts
from app.bot.keyboards import main_menu
from app.db.models import User


async def start(message: Message, user: User, webapp_url: str | None) -> None:
    if user.is_onboarded:
        text = texts.welcome_back(user.first_name)
    else:
        text = texts.welcome_new(user.first_name)
    hint = texts.OPEN_APP_HINT if webapp_url else texts.APP_NOT_READY
    await message.answer(f"{text}\n\n{hint}", reply_markup=main_menu(webapp_url))


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(start, CommandStart())
    return router
