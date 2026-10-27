from datetime import datetime

from sqlalchemy import ColumnElement, CompoundSelect, and_, or_, select, union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Block, User
from app.domain.time import as_utc, utcnow


async def upsert_telegram_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    first_name: str,
    username: str | None,
    language_code: str | None,
    now: datetime | None = None,
) -> User:
    """Находит пользователя по Telegram ID или создаёт его. Обновляет имя и время последнего визита.

    Используется и ботом, и (позже) API мини-приложения.
    """
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        try:
            # Два апдейта от нового пользователя могут прийти одновременно — второй найдёт уже созданную запись
            async with session.begin_nested():
                user = User(telegram_id=telegram_id, first_name=first_name)
                session.add(user)
        except IntegrityError:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

    user.first_name = first_name[:128]
    user.username = username
    user.language_code = language_code[:8] if language_code else None
    user.last_seen_at = now or utcnow()
    await session.flush()
    return user


def is_ban_active(user: User, now: datetime | None = None) -> bool:
    if not user.is_banned:
        return False
    if user.banned_until is None:
        return True  # бан навсегда
    return as_utc(user.banned_until) > (now or utcnow())


def ban_inactive_clause(now: datetime) -> ColumnElement[bool]:
    """То же, что `not is_ban_active`, но для SQL-запросов."""
    return or_(
        User.is_banned.is_(False),
        and_(User.banned_until.is_not(None), User.banned_until <= now),
    )


def blocked_user_ids(user_id: int) -> CompoundSelect:
    """Все, кого пользователь заблокировал, и все, кто заблокировал его, — для `.not_in(...)` в запросах."""
    return union(
        select(Block.blocked_id).where(Block.blocker_id == user_id),
        select(Block.blocker_id).where(Block.blocked_id == user_id),
    )
