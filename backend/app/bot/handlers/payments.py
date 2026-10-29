"""Оплата звёздами: проверка перед оплатой, выдача после неё, возврат по команде админа.

Счёт выставляет API (routes/shop.py) по серверному каталогу; здесь сверяем, что в оплате то же самое.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.handlers.admin import can_grant
from app.db.models import Payment, User
from app.domain.time import utcnow
from app.services.payments import fulfil, owns, parse_payload, take_back

logger = logging.getLogger(__name__)


async def pre_checkout(query: PreCheckoutQuery, session: AsyncSession, user: User) -> None:
    """Последняя проверка до списания: тот же товар, тот же покупатель, та же сумма, вещи ещё нет."""
    parsed = parse_payload(query.invoice_payload)
    ok = (
        parsed is not None
        and query.currency == "XTR"
        and parsed[1] == user.id
        and parsed[2] == query.total_amount
        and not (parsed[0].kind == "cosmetic" and await owns(session, user.id, parsed[0].id))
    )
    await query.answer(ok=ok, error_message=None if ok else texts.PAYMENT_REJECTED)


async def paid(message: Message, session: AsyncSession, user: User) -> None:
    payment = message.successful_payment
    parsed = parse_payload(payment.invoice_payload)
    if parsed is None:
        logger.error("Оплата с непонятным payload %r", payment.invoice_payload)
        return
    product = parsed[0]
    renewal = bool(payment.is_recurring and not payment.is_first_recurring)
    fresh = await fulfil(
        session, user, product, payment.total_amount, payment.telegram_payment_charge_id, renewal, utcnow()
    )
    if fresh and not renewal:
        await message.answer(texts.payment_thanks(product.title))


async def refund(
    message: Message, command: CommandObject, session: AsyncSession, user: User, admin_ids: frozenset[int]
) -> None:
    if not can_grant(user, admin_ids):
        await message.answer(texts.FALLBACK)
        return
    if not command.args:
        await message.answer(texts.REFUND_USAGE)
        return
    payment = await session.scalar(select(Payment).where(Payment.telegram_charge_id == command.args.strip()))
    if payment is None:
        await message.answer(texts.REFUND_NOT_FOUND)
        return
    if payment.refunded_at is not None:
        await message.answer(texts.REFUND_ALREADY)
        return
    buyer = await session.get(User, payment.user_id)
    await message.bot.refund_star_payment(
        user_id=buyer.telegram_id, telegram_payment_charge_id=payment.telegram_charge_id
    )
    await take_back(session, payment, utcnow())
    await message.answer(texts.REFUND_DONE)


def create_router() -> Router:
    router = Router(name="payments")
    router.pre_checkout_query.register(pre_checkout)
    router.message.register(paid, F.successful_payment)
    router.message.register(refund, Command("refund"))
    return router
