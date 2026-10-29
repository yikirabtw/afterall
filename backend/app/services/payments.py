"""Оплата звёздами: что выдать за оплату и что забрать при возврате. Проверка цены — в боте (pre_checkout)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AgeGroup, SubscriptionSource
from app.db.models import BoostCredits, Payment, Profile, User, UserItem
from app.domain.catalog import PRODUCTS, SPENDING_WINDOW, SUBSCRIPTION_PERIOD, TEEN_MONTHLY_STARS, Product
from app.services.plans import grant, revoke


def payload(product: Product, user_id: int, stars: int) -> str:
    """Что зашито в счёт: товар, кому и за сколько — бот сверит это перед оплатой."""
    return f"{product.id}:{user_id}:{stars}"


def parse_payload(raw: str) -> tuple[Product, int, int] | None:
    try:
        product_id, user_id, stars = raw.split(":")
        return PRODUCTS[product_id], int(user_id), int(stars)
    except (KeyError, ValueError):
        return None


async def spent_recently(session: AsyncSession, user_id: int, now: datetime) -> int:
    return await session.scalar(
        select(func.coalesce(func.sum(Payment.stars), 0)).where(
            Payment.user_id == user_id, Payment.refunded_at.is_(None), Payment.created_at > now - SPENDING_WINDOW
        )
    )


def teen_limit(age_group: AgeGroup | None) -> int | None:
    return TEEN_MONTHLY_STARS.get(age_group) if age_group else None


async def owns(session: AsyncSession, user_id: int, item_id: str) -> bool:
    return await session.get(UserItem, (user_id, item_id)) is not None


async def fulfil(
    session: AsyncSession,
    user: User,
    product: Product,
    stars: int,
    charge_id: str,
    is_recurring: bool,
    now: datetime,
) -> bool:
    """Записать оплату и выдать купленное. Повтор того же платежа (Telegram может прислать дважды) — ничего."""
    if await session.scalar(select(Payment.id).where(Payment.telegram_charge_id == charge_id)) is not None:
        return False
    session.add(
        Payment(
            user_id=user.id,
            product_id=product.id,
            stars=stars,
            telegram_charge_id=charge_id,
            is_recurring=is_recurring,
            created_at=now,
        )
    )
    if product.kind == "plan":
        await grant(session, user.id, product.plan, SUBSCRIPTION_PERIOD.days, None, now, SubscriptionSource.STARS)
    elif product.kind == "boosts":
        credits = await session.get(BoostCredits, (user.id, product.boost_kind))
        if credits is None:
            session.add(BoostCredits(user_id=user.id, kind=product.boost_kind, amount=product.boost_count))
        else:
            credits.amount += product.boost_count
    elif not await owns(session, user.id, product.id):
        session.add(UserItem(user_id=user.id, item_id=product.id, acquired_at=now, source="stars"))
    return True


async def take_back(session: AsyncSession, payment: Payment, now: datetime) -> None:
    """После возврата звёзд — забрать купленное: подписку закончить, бусты списать, вещь убрать."""
    product = PRODUCTS.get(payment.product_id)
    payment.refunded_at = now
    if product is None:
        return
    if product.kind == "plan":
        await revoke(session, payment.user_id, now, product.plan)
    elif product.kind == "boosts":
        credits = await session.get(BoostCredits, (payment.user_id, product.boost_kind))
        if credits is not None:
            credits.amount = max(0, credits.amount - product.boost_count)
    else:
        item = await session.get(UserItem, (payment.user_id, product.id))
        if item is not None:
            await session.delete(item)
        profile = await session.get(Profile, payment.user_id)
        if profile is not None and profile.equipped and product.id in profile.equipped.values():
            profile.equipped = {slot: item_id for slot, item_id in profile.equipped.items() if item_id != product.id}
