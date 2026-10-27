from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot import texts
from app.services.users import is_ban_active, upsert_telegram_user

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class DbSessionMiddleware(BaseMiddleware):
    """Одна сессия и одна транзакция на апдейт: коммит, если хендлер отработал, откат — если упал."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self.session_maker.begin() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Регистрирует пользователя при первом сообщении, кладёт его в data["user"], отсекает забаненных."""

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        telegram_user: TelegramUser | None = data.get("event_from_user")
        if telegram_user is None or telegram_user.is_bot:
            return await handler(event, data)

        user = await upsert_telegram_user(
            data["session"],
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code,
        )
        if is_ban_active(user):
            await self._notify_banned(event)
            return None

        data["user"] = user
        return await handler(event, data)

    @staticmethod
    async def _notify_banned(event: TelegramObject) -> None:
        if not isinstance(event, Update):
            return
        if event.message:
            await event.message.answer(texts.BANNED)
        elif event.callback_query:
            await event.callback_query.answer(texts.BANNED, show_alert=True)
