"""Команды админа в боте: выдать или снять подписку (тестерам, в подарок).

Права — только у админов (роль admin или ADMIN_TELEGRAM_IDS); модераторам подписки раздавать нельзя.
Остальным команды не видны: в ответ — тот же текст, что на любое непонятное сообщение.
"""

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.db.enums import PlanKind, UserRole
from app.db.models import Profile, User, UserItem
from app.domain.cosmetics import ALL_ITEMS
from app.domain.plans import GRANT_DEFAULT, GRANT_MAX_DAYS
from app.domain.time import utcnow
from app.services.plans import grant, revoke

logger = logging.getLogger(__name__)


def can_grant(user: User, admin_ids: frozenset[int]) -> bool:
    return user.role == UserRole.ADMIN or user.telegram_id in admin_ids


def _parse(args: str | None) -> tuple[str | None, int]:
    """«@ник 30», «123456789», «7» → (кто или None — сам админ, дней).

    Число больше GRANT_MAX_DAYS — это Telegram ID (настоящие ID всегда больше), не больше — дни.
    """
    who, days = None, GRANT_DEFAULT.days
    for token in (args or "").split():
        if token.startswith("@") or (token.isdigit() and int(token) > GRANT_MAX_DAYS):
            who = token
        elif token.isdigit():
            days = max(1, int(token))
    return who, days


async def _find(session: AsyncSession, who: str) -> User | None:
    if who.startswith("@"):
        return await session.scalar(select(User).where(func.lower(User.username) == who[1:].lower()))
    return await session.scalar(select(User).where(User.telegram_id == int(who)))


async def _name(session: AsyncSession, user: User) -> str:
    profile = await session.get(Profile, user.id)
    return profile.display_name if profile else user.first_name


async def change_plan(
    message: Message, command: CommandObject, session: AsyncSession, user: User, admin_ids: frozenset[int]
) -> None:
    if not can_grant(user, admin_ids):
        await message.answer(texts.FALLBACK)
        return
    if command.args and command.args.strip() in ("?", "help"):
        await message.answer(texts.ADMIN_PLAN_HELP)
        return
    who, days = _parse(command.args)
    target = user if who is None else await _find(session, who)
    if target is None:
        await message.answer(texts.ADMIN_USER_NOT_FOUND)
        return

    now = utcnow()
    name = await _name(session, target)
    if command.command == "free":
        await message.answer(texts.plan_revoked(name, await revoke(session, target.id, now)))
        return
    until = await grant(session, target.id, PlanKind(command.command), days, user.id, now)
    await message.answer(texts.plan_granted(name, command.command, until))
    if target.id != user.id:
        try:
            await message.bot.send_message(target.telegram_id, texts.plan_gift(command.command, until))
        except TelegramAPIError:
            # Человек ни разу не писал боту — подписка всё равно выдана, просто без сообщения
            logger.info("Не удалось сообщить о подписке пользователю %s", target.id)


async def give_item(
    message: Message, command: CommandObject, session: AsyncSession, user: User, admin_ids: frozenset[int]
) -> None:
    """/item frame-neon — себе, /item @ник frame-neon — человеку. Для проверки косметики, пока оплата выключена."""
    if not can_grant(user, admin_ids):
        await message.answer(texts.FALLBACK)
        return
    tokens = (command.args or "").split()
    item_id = next((token for token in tokens if token in ALL_ITEMS), None)
    who = next((token for token in tokens if token.startswith("@") or token.isdigit()), None)
    if item_id is None:
        await message.answer(texts.admin_item_help(sorted(ALL_ITEMS)))
        return
    target = user if who is None else await _find(session, who)
    if target is None:
        await message.answer(texts.ADMIN_USER_NOT_FOUND)
        return
    if await session.get(UserItem, (target.id, item_id)) is None:
        session.add(UserItem(user_id=target.id, item_id=item_id, acquired_at=utcnow(), source="admin"))
    await message.answer(texts.item_given(await _name(session, target), item_id))


def create_router() -> Router:
    router = Router(name="admin")
    router.message.register(change_plan, Command("premium", "plus", "free"))
    router.message.register(give_item, Command("item"))
    return router
