"""Оплата звёздами: витрина и цены, счёт, проверка перед оплатой, выдача купленного, возврат."""

from datetime import datetime, timezone

import pytest
from aiogram import Bot
from aiogram.methods import AnswerPreCheckoutQuery, CreateInvoiceLink, RefundStarPayment
from aiogram.types import Chat, Message, PreCheckoutQuery, SuccessfulPayment, Update
from aiogram.types import User as TelegramUser
from conftest import ADMIN_TELEGRAM_ID
from fakes import INVOICE_URL, RecordingSession
from sqlalchemy import select

from app.bot.dispatcher import build_dispatcher
from app.db.enums import SubscriptionSource
from app.db.models import BoostCredits, Payment, Subscription, UserItem
from app.domain.time import utcnow
from app.services.plans import plan_of


def enable_payments(client) -> None:
    client._transport.app.state.payments_enabled = True  # type: ignore[attr-defined]


async def invoice(client, player, product_id: str, expect: int = 200) -> dict:
    response = await client.post("/api/shop/invoice", json={"product_id": product_id}, headers=player.headers)
    assert response.status_code == expect, response.text
    return response.json()


# --- Витрина и счёт ---


async def test_shop_prices_and_subscriber_discount(client, make_player, set_plan):
    me = await make_player(age=25)
    shop = (await client.get("/api/shop", headers=me.headers)).json()
    assert shop["payments_enabled"] is False and shop["spending_limit"] is None
    products = {p["id"]: p for p in shop["products"]}
    assert (products["premium"]["price"], products["frame-neon"]["price"]) == (199, 35)

    await set_plan("plus", user_id=me.id)
    products = {p["id"]: p for p in (await client.get("/api/shop", headers=me.headers)).json()["products"]}
    assert products["frame-neon"]["price"] == 28  # подписчикам −20% на косметику
    assert products["party-hour"]["price"] == 15  # бусты — без скидки


async def test_invoice_only_when_payments_enabled(client, notifier, make_player):
    me = await make_player(age=25)
    assert (await invoice(client, me, "plus", 403))["detail"] == "payments_disabled"

    enable_payments(client)
    assert (await invoice(client, me, "plus"))["url"] == INVOICE_URL
    [request] = [r for r in notifier.bot.session.requests if isinstance(r, CreateInvoiceLink)]
    assert (request.currency, request.prices[0].amount, request.subscription_period) == ("XTR", 99, 30 * 24 * 3600)
    assert request.payload == f"plus:{me.id}:99"
    assert (await invoice(client, me, "nope", 404))["detail"] == "unknown_product"


async def test_invoice_refuses_active_plan_and_owned_item(client, make_player, set_plan, session_maker):
    me = await make_player(age=25)
    enable_payments(client)
    await set_plan("plus", user_id=me.id)
    assert (await invoice(client, me, "premium", 409))["detail"] == "plan_active"

    async with session_maker.begin() as session:
        session.add(UserItem(user_id=me.id, item_id="frame-neon", acquired_at=utcnow()))
    assert (await invoice(client, me, "frame-neon", 409))["detail"] == "already_owned"


async def test_teen_spending_limit(client, make_player, session_maker):
    teen = await make_player(age=14)
    enable_payments(client)
    shop = (await client.get("/api/shop", headers=teen.headers)).json()
    assert (shop["spending_limit"], shop["spent"]) == (300, 0)

    async with session_maker.begin() as session:
        session.add(Payment(user_id=teen.id, product_id="plus", stars=280, telegram_charge_id="c1", created_at=utcnow()))
    assert (await invoice(client, teen, "party-hour"))["url"] == INVOICE_URL  # 280 + 15 ≤ 300
    assert (await invoice(client, teen, "profile-evening", 403))["detail"] == "teen_spending_limit"  # 280 + 25 > 300


# --- Бот: проверка, выдача, возврат ---


@pytest.fixture
def bot() -> Bot:
    return Bot("42:TEST", session=RecordingSession())


def buyer(player) -> TelegramUser:
    return TelegramUser(id=player.telegram_id, is_bot=False, first_name=player.username)


def checkout(player, payload: str, amount: int) -> Update:
    return Update(
        update_id=1,
        pre_checkout_query=PreCheckoutQuery(
            id="q1", from_user=buyer(player), currency="XTR", total_amount=amount, invoice_payload=payload
        ),
    )


def paid(player, payload: str, amount: int, charge: str, recurring: bool = False, first: bool = False) -> Update:
    return Update(
        update_id=2,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=player.telegram_id, type="private"),
            from_user=buyer(player),
            successful_payment=SuccessfulPayment(
                currency="XTR",
                total_amount=amount,
                invoice_payload=payload,
                telegram_payment_charge_id=charge,
                provider_payment_charge_id="",
                is_recurring=recurring or None,
                is_first_recurring=first or None,
            ),
        ),
    )


async def test_pre_checkout_checks_buyer_and_price(bot, session_maker, make_player):
    me, other = await make_player(), await make_player()
    dispatcher = build_dispatcher(session_maker, None)

    await dispatcher.feed_update(bot, checkout(me, f"plus:{me.id}:99", 99))
    await dispatcher.feed_update(bot, checkout(me, f"plus:{me.id}:99", 1))  # сумма не та
    await dispatcher.feed_update(bot, checkout(me, f"plus:{other.id}:99", 99))  # чужой счёт

    answers = [r.ok for r in bot.session.requests if isinstance(r, AnswerPreCheckoutQuery)]
    assert answers == [True, False, False]


async def test_payment_grants_and_refund_takes_back(bot, session_maker, make_player):
    me = await make_player()
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))

    await dispatcher.feed_update(bot, paid(me, f"premium:{me.id}:199", 199, "ch-premium", True, True))
    await dispatcher.feed_update(bot, paid(me, f"party-pack:{me.id}:59", 59, "ch-pack"))
    await dispatcher.feed_update(bot, paid(me, f"frame-neon:{me.id}:28", 28, "ch-frame"))
    await dispatcher.feed_update(bot, paid(me, f"frame-neon:{me.id}:28", 28, "ch-frame"))  # Telegram прислал дважды

    async with session_maker() as session:
        plan, _ = await plan_of(session, me.id, utcnow())
        source = await session.scalar(select(Subscription.source).where(Subscription.user_id == me.id))
        credits = await session.get(BoostCredits, (me.id, "lobby"))
        payments = list(await session.scalars(select(Payment.telegram_charge_id)))
        item = await session.get(UserItem, (me.id, "frame-neon"))
    assert (plan, source, credits.amount, item is not None) == ("premium", SubscriptionSource.STARS, 5, True)
    assert sorted(payments) == ["ch-frame", "ch-pack", "ch-premium"]

    # Возврат — только админ; звёзды возвращаются, купленное забирается
    admin_command = Update(
        update_id=3,
        message=Message(
            message_id=2,
            date=datetime.now(timezone.utc),
            chat=Chat(id=ADMIN_TELEGRAM_ID, type="private"),
            from_user=TelegramUser(id=ADMIN_TELEGRAM_ID, is_bot=False, first_name="Админ"),
            text="/refund ch-premium",
        ),
    )
    await dispatcher.feed_update(bot, admin_command)

    [refund] = [r for r in bot.session.requests if isinstance(r, RefundStarPayment)]
    assert (refund.user_id, refund.telegram_payment_charge_id) == (me.telegram_id, "ch-premium")
    async with session_maker() as session:
        assert (await plan_of(session, me.id, utcnow()))[0] == "free"
        payment = await session.scalar(select(Payment).where(Payment.telegram_charge_id == "ch-premium"))
        assert payment.refunded_at is not None
