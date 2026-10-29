"""Уведомления в боте: мэтч, новое сообщение, отклик на пати, решение по отклику; жалобы — модераторам.

Шлёт их API после ответа (BackgroundTasks), поэтому медленный Telegram не тормозит приложение,
а ошибка отправки (человек остановил бота и т. п.) ничего не ломает.

Отправляем только с сервера — там бот работает через вебхук внутри API. Локально бота нет, и уведомления
пишутся в лог: токен боевого бота на компьютере не используем, иначе сообщения ушли бы настоящим людям.
"""

import logging
from dataclasses import dataclass
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from app.db.models import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Note:
    telegram_id: int
    text: str  # HTML: всё, что ввели люди, экранировано в bot/texts.py
    button: str | None = None
    open_path: str | None = None  # какой экран открыть в мини-приложении: «chat/direct/12», «lobby/5»…
    markup: InlineKeyboardMarkup | None = None  # готовые кнопки — например, у жалобы для модераторов


class Notifier:
    def __init__(self, bot: Bot | None, webapp_url: str | None, admin_ids: frozenset[int] = frozenset()) -> None:
        self.bot = bot
        self.webapp_url = webapp_url
        self.admin_ids = admin_ids  # Telegram ID админов из настроек — им жалобы приходят, даже без роли в базе

    async def send(self, notes: list[Note]) -> None:
        for note in notes:
            if self.bot is None:
                logger.info("Уведомление для %s (бота нет — не отправлено): %s", note.telegram_id, note.text)
                continue
            try:
                await self.bot.send_message(note.telegram_id, note.text, reply_markup=self._markup(note))
            except Exception:
                logger.warning("Не удалось отправить уведомление %s", note.telegram_id, exc_info=True)

    def _markup(self, note: Note) -> InlineKeyboardMarkup | None:
        if note.markup is not None:
            return note.markup
        if note.button is None or note.open_path is None or not self.webapp_url:
            return None
        button = InlineKeyboardButton(text=note.button, web_app=WebAppInfo(url=self.app_link(note.open_path)))
        return InlineKeyboardMarkup(inline_keyboard=[[button]])

    def app_link(self, path: str) -> str:
        """Ссылка, по которой мини-приложение сразу откроет нужный экран (читает ?open= при запуске)."""
        separator = "&" if "?" in self.webapp_url else "?"
        return f"{self.webapp_url}{separator}open={quote(path, safe='/')}"


async def moderator_telegram_ids(session: AsyncSession, admin_ids: frozenset[int]) -> set[int]:
    """Кому слать жалобы: модераторы и админы из базы плюс админы из настроек."""
    staff = or_(User.role.in_((UserRole.MODERATOR, UserRole.ADMIN)), User.telegram_id.in_(admin_ids))
    in_db = await session.scalars(select(User.telegram_id).where(staff))
    return set(in_db) | set(admin_ids)
