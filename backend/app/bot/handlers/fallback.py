from aiogram import Router
from aiogram.types import Message

from app.bot import texts


async def unknown_message(message: Message) -> None:
    await message.answer(texts.FALLBACK)


def create_router() -> Router:
    router = Router(name="fallback")
    router.message.register(unknown_message)
    return router
