"""Косметика: какие бывают вещи, что из них можно надеть, подарок Premium.

Вещь — только оформление, преимуществ не даёт. Тип вещи — по началу id (frame-, bg-, badge-, match-, theme-).
Тема — настройка телефона: её не «надевают» на сервере, а включают в профиле, если она есть.
"""

from datetime import timedelta

from app.domain.catalog import PRODUCTS

SLOTS = {"frame": "frame-", "background": "bg-", "badge": "badge-", "match": "match-"}
THEME_PREFIX = "theme-"
# Значки за активность — не продаются, только зарабатываются
EARNABLE = {"badge-first", "badge-veteran"}
ALL_ITEMS = {product.id for product in PRODUCTS.values() if product.kind == "cosmetic"} | EARNABLE

GIFT_PERIOD = timedelta(days=30)  # Premium: одна вещь в подарок раз в 30 дней


def slot_of(item_id: str) -> str | None:
    return next((slot for slot, prefix in SLOTS.items() if item_id.startswith(prefix)), None)
