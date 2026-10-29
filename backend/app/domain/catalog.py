"""Что продаётся за звёзды Telegram и почём (решения пользователя — docs/ROADMAP.md → «Монетизация»).

Цены — здесь, на сервере: счёт выставляется по ним, а не по тому, что прислал телефон. Идентификаторы совпадают
с витриной (webapp/src/shop.ts). Без лутбоксов: за свою цену — ровно то, что описано.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from app.db.enums import AgeGroup, BoostKind, PlanKind

SUBSCRIPTION_PERIOD = timedelta(days=30)  # подписка звёздами в Telegram — ровно 30 дней, потом продление
SUBSCRIBER_DISCOUNT = 0.2  # Plus и Premium — скидка на косметику

# Лимит трат за 30 дней для младших групп (дорожная карта: «Лимиты трат для младших групп»)
TEEN_MONTHLY_STARS: dict[AgeGroup, int] = {AgeGroup.TEEN_13_15: 300, AgeGroup.TEEN_16_17: 600}
SPENDING_WINDOW = timedelta(days=30)


@dataclass(frozen=True)
class Product:
    id: str
    kind: Literal["plan", "boosts", "cosmetic"]
    title: str  # заголовок счёта в Telegram (до 32 символов)
    description: str  # описание в счёте (до 255)
    stars: int
    plan: PlanKind | None = None
    boost_kind: BoostKind | None = None
    boost_count: int = 0


def _cosmetic(item_id: str, title: str, stars: int) -> Product:
    return Product(item_id, "cosmetic", title, f"{title} — оформление для профиля навсегда.", stars)


PRODUCTS: dict[str, Product] = {
    product.id: product
    for product in [
        Product(
            "plus", "plan", "afterall Plus",
            "3 фото, до 5 пати, кто лайкнул, возврат анкет, буст в неделю. Продлевается раз в 30 дней — "
            "отменить можно в любой момент.",
            99, plan=PlanKind.PLUS,
        ),
        Product(
            "premium", "plan", "afterall Premium",
            "Всё из Plus, до 10 пати, возврат анкет без лимита, 3 буста в неделю, закрытые пати, наборы ленты. "
            "Продлевается раз в 30 дней — отменить можно в любой момент.",
            199, plan=PlanKind.PREMIUM,
        ),
        Product("party-hour", "boosts", "Поднять пати", "Один подъём своей пати в ленте на час.", 15,
                boost_kind=BoostKind.LOBBY, boost_count=1),
        Product("profile-evening", "boosts", "Анкета первой", "Анкета первой в ленте людей на вечер (6 часов).", 25,
                boost_kind=BoostKind.PROFILE, boost_count=1),
        Product("party-pack", "boosts", "5 подъёмов пати", "Пять подъёмов пати на час. Не сгорают.", 59,
                boost_kind=BoostKind.LOBBY, boost_count=5),
        _cosmetic("frame-neon", "Рамка «Неон»", 35),
        _cosmetic("frame-pixel", "Рамка «Пиксель»", 25),
        _cosmetic("frame-spikes", "Рамка «Шипы»", 45),
        _cosmetic("frame-lamp", "Рамка «Лампа»", 45),
        _cosmetic("bg-smoke", "Фон «Дым»", 49),
        _cosmetic("bg-light", "Фон «Полоса света»", 39),
        _cosmetic("bg-grid", "Фон «Сетка»", 29),
        _cosmetic("badge-night", "Значок «Ночной игрок»", 15),
        _cosmetic("badge-heart", "Значок «Пиксельное сердце»", 19),
        _cosmetic("match-red", "Мэтч «Красная лампа»", 39),
        _cosmetic("match-neon", "Мэтч «Неоновая вывеска»", 49),
        _cosmetic("theme-blue", "Тема «Синий час»", 49),
        _cosmetic("theme-sepia", "Тема «Сепия»", 49),
    ]
}


def price_for(product: Product, subscriber: bool) -> int:
    """Цена для этого человека: косметика подписчикам — со скидкой."""
    if product.kind == "cosmetic" and subscriber:
        return round(product.stars * (1 - SUBSCRIBER_DISCOUNT))
    return product.stars
