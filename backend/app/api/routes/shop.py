"""Магазин: цены, счёт на оплату звёздами Telegram, история покупок, отмена продления подписки.

Оплата выключена флагом PAYMENTS_ENABLED, пока пользователь сам не решит. Счёт выставляет бот (на сервере
он работает через вебхук); выдачу купленного делает бот после оплаты — bot/handlers/payments.py.
"""

from aiogram.types import LabeledPrice
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import OnboardedUser, SessionDep
from app.api.schemas import InvoiceIn, InvoiceOut, PaymentOut, ShopOut, ShopProductOut
from app.db.models import Payment, UserItem
from app.domain.catalog import PRODUCTS, SUBSCRIPTION_PERIOD, price_for
from app.domain.time import utcnow
from app.services.payments import owns, payload, spent_recently, teen_limit
from app.services.plans import plan_of

router = APIRouter(prefix="/shop", tags=["магазин"])

PAYMENTS_HISTORY_MAX = 100


@router.get("", response_model=ShopOut)
async def shop(request: Request, user: OnboardedUser, session: SessionDep) -> ShopOut:
    now = utcnow()
    plan, _ = await plan_of(session, user.id, now)
    owned = set(await session.scalars(select(UserItem.item_id).where(UserItem.user_id == user.id)))
    return ShopOut(
        payments_enabled=request.app.state.payments_enabled,
        products=[
            ShopProductOut(
                id=product.id,
                kind=product.kind,
                stars=product.stars,
                price=price_for(product, plan != "free"),
                owned=product.id in owned,
            )
            for product in PRODUCTS.values()
        ],
        spending_limit=teen_limit(user.age_group),
        spent=await spent_recently(session, user.id, now),
    )


@router.post("/invoice", response_model=InvoiceOut)
async def invoice(body: InvoiceIn, request: Request, user: OnboardedUser, session: SessionDep) -> InvoiceOut:
    """Счёт в звёздах. Цена — по серверному каталогу; подписки — с продлением раз в 30 дней."""
    if not request.app.state.payments_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="payments_disabled")
    bot = request.app.state.notifier.bot
    if bot is None:  # локально бота нет
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="payments_unavailable")
    product = PRODUCTS.get(body.product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown_product")

    now = utcnow()
    plan, _ = await plan_of(session, user.id, now)
    if product.kind == "plan" and plan != "free":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="plan_active")
    if product.kind == "cosmetic" and await owns(session, user.id, product.id):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="already_owned")
    price = price_for(product, plan != "free")
    limit = teen_limit(user.age_group)
    if limit is not None and await spent_recently(session, user.id, now) + price > limit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="teen_spending_limit")

    url = await bot.create_invoice_link(
        title=product.title,
        description=product.description,
        payload=payload(product, user.id, price),
        currency="XTR",
        prices=[LabeledPrice(label=product.title, amount=price)],
        subscription_period=int(SUBSCRIPTION_PERIOD.total_seconds()) if product.kind == "plan" else None,
    )
    return InvoiceOut(url=url)


@router.get("/payments", response_model=list[PaymentOut])
async def my_payments(user: OnboardedUser, session: SessionDep) -> list[PaymentOut]:
    """История покупок, новые сверху."""
    payments = await session.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .limit(PAYMENTS_HISTORY_MAX)
    )
    return [
        PaymentOut(
            id=payment.id,
            product_id=payment.product_id,
            title=PRODUCTS[payment.product_id].title if payment.product_id in PRODUCTS else payment.product_id,
            stars=payment.stars,
            is_recurring=payment.is_recurring,
            refunded=payment.refunded_at is not None,
            created_at=payment.created_at,
        )
        for payment in payments
    ]


@router.post("/subscription/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_subscription(request: Request, user: OnboardedUser, session: SessionDep) -> Response:
    """Отменить продление — в один тап. Оплаченный месяц остаётся до конца."""
    bot = request.app.state.notifier.bot
    if bot is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="payments_unavailable")
    plan_ids = [product.id for product in PRODUCTS.values() if product.kind == "plan"]
    first = await session.scalar(
        select(Payment)
        .where(
            Payment.user_id == user.id,
            Payment.product_id.in_(plan_ids),
            Payment.is_recurring.is_(False),
            Payment.refunded_at.is_(None),
        )
        .order_by(Payment.created_at.desc())
    )
    if first is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no_subscription")
    await bot.edit_user_star_subscription(
        user_id=user.telegram_id, telegram_payment_charge_id=first.telegram_charge_id, is_canceled=True
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
