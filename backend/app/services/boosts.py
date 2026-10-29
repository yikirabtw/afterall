"""Бусты: что сейчас поднято и сколько бустов у человека осталось."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BoostKind, BoostSource
from app.db.models import Boost, BoostCredits
from app.domain.boosts import DAY, WEEK, WEEKLY_FREE
from app.domain.plans import Plan
from app.domain.time import as_utc


def _active(now: datetime):
    return (Boost.starts_at <= now, Boost.ends_at > now)


async def boosted_lobbies(
    session: AsyncSession, now: datetime, lobby_ids: Iterable[int] | None = None
) -> dict[int, datetime]:
    """Поднятые сейчас пати → до какого момента."""
    query = select(Boost.lobby_id, Boost.ends_at).where(Boost.kind == BoostKind.LOBBY, *_active(now))
    if lobby_ids is not None:
        query = query.where(Boost.lobby_id.in_(list(lobby_ids)))
    return {lobby_id: as_utc(ends_at) for lobby_id, ends_at in await session.execute(query)}


async def boosted_profiles(session: AsyncSession, user_ids: Iterable[int], now: datetime) -> dict[int, datetime]:
    """Чьи анкеты сейчас подняты → до какого момента."""
    rows = await session.execute(
        select(Boost.user_id, Boost.ends_at).where(
            Boost.kind == BoostKind.PROFILE, Boost.user_id.in_(list(user_ids)), *_active(now)
        )
    )
    return {user_id: as_utc(ends_at) for user_id, ends_at in rows}


@dataclass
class Allowance:
    weekly_total: int
    weekly_left: int
    credits: int
    today: int  # сколько бустов уже сегодня (лимит DAILY_MAX)


async def allowance(
    session: AsyncSession, user_id: int, plan: Plan, now: datetime, kind: BoostKind | None = None
) -> Allowance:
    """Остаток бустов. kind — сколько купленных именно этого вида; без него — всех видов вместе."""
    weekly_used = await session.scalar(
        select(func.count(Boost.id)).where(
            Boost.user_id == user_id, Boost.source == BoostSource.WEEKLY, Boost.created_at > now - WEEK
        )
    )
    today = await session.scalar(
        select(func.count(Boost.id)).where(Boost.user_id == user_id, Boost.created_at > now - DAY)
    )
    credits_query = select(func.coalesce(func.sum(BoostCredits.amount), 0)).where(BoostCredits.user_id == user_id)
    if kind is not None:
        credits_query = credits_query.where(BoostCredits.kind == kind)
    credits = await session.scalar(credits_query)
    total = WEEKLY_FREE[plan]
    return Allowance(
        weekly_total=total,
        weekly_left=max(0, total - weekly_used),
        credits=credits,
        today=today,
    )
