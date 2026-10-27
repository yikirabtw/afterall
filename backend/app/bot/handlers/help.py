from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import texts
from app.bot.keyboards import HELP_CALLBACK


async def help_command(message: Message) -> None:
    await message.answer(texts.HELP)


async def help_button(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(texts.HELP)
    await callback.answer()


def create_router() -> Router:
    router = Router(name="help")
    router.message.register(help_command, Command("help"))
    router.callback_query.register(help_button, F.data == HELP_CALLBACK)
    return router
