"""Действующий тариф пользователя и выдача подписок."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PlanKind, SubscriptionSource
from app.db.models import Subscription
from app.domain.plans import PLAN_ORDER, Plan
from app.domain.time import as_utc


def _active(now: datetime):
    return (Subscription.starts_at <= now, Subscription.ends_at > now)


async def plans_of(session: AsyncSession, user_ids: Iterable[int], now: datetime) -> dict[int, Plan]:
    """Тариф каждого из списка — одним запросом (для ленты, мэтчей). Кого нет в ответе — бесплатный."""
    ids = list(set(user_ids))
    if not ids:
        return {}
    plans: dict[int, Plan] = {}
    for user_id, plan in await session.execute(
        select(Subscription.user_id, Subscription.plan).where(Subscription.user_id.in_(ids), *_active(now))
    ):
        if PLAN_ORDER[plan.value] > PLAN_ORDER[plans.get(user_id, "free")]:
            plans[user_id] = plan.value
    return plans


async def plan_of(session: AsyncSession, user_id: int, now: datetime) -> tuple[Plan, datetime | None]:
    """Самый высокий действующий тариф и до какого момента он оплачен."""
    subscriptions = list(
        await session.scalars(select(Subscription).where(Subscription.user_id == user_id, *_active(now)))
    )
    if not subscriptions:
        return "free", None
    best = max(subscriptions, key=lambda item: PLAN_ORDER[item.plan.value]).plan
    until = max(as_utc(item.ends_at) for item in subscriptions if item.plan == best)
    return best.value, until


async def grant(
    session: AsyncSession, user_id: int, plan: PlanKind, days: int, granted_by_id: int | None, now: datetime
) -> datetime:
    """Выдать подписку на days дней. Если такая уже действует — продлить её. Возвращает новый срок окончания."""
    current = await session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.plan == plan, *_active(now))
        .order_by(Subscription.ends_at.desc())
    )
    if current is not None:
        current.ends_at = as_utc(current.ends_at) + timedelta(days=days)
        return current.ends_at
    ends_at = now + timedelta(days=days)
    session.add(
        Subscription(
            user_id=user_id,
            plan=plan,
            starts_at=now,
            ends_at=ends_at,
            source=SubscriptionSource.GRANT,
            granted_by_id=granted_by_id,
        )
    )
    return ends_at


async def revoke(session: AsyncSession, user_id: int, now: datetime) -> int:
    """Закончить все действующие подписки прямо сейчас. Возвращает, сколько было."""
    active = list(await session.scalars(select(Subscription).where(Subscription.user_id == user_id, *_active(now))))
    for subscription in active:
        subscription.ends_at = now
    return len(active)
