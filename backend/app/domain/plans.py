"""Тарифы и что они дают (решения пользователя, docs/ROADMAP.md → «Монетизация»).

Безопасность от тарифа не зависит: возраст, блокировки, жалобы, мэтчи и чаты — одинаковы для всех.
"""

from datetime import timedelta
from typing import Literal

Plan = Literal["free", "plus", "premium"]

PLAN_ORDER: dict[Plan, int] = {"free": 0, "plus": 1, "premium": 2}

PHOTOS_MAX = 3  # больше трёх фото нет ни у кого
# Бесплатно — одно фото. Кто загрузил больше до появления тарифов, их не теряет: лимит — только на новые
PHOTO_LIMITS: dict[Plan, int] = {"free": 1, "plus": 3, "premium": 3}
ACTIVE_LOBBY_LIMITS: dict[Plan, int] = {"free": 2, "plus": 5, "premium": 10}

# «Кто лайкнул» — списком только с подпиской; бесплатно — одно число
LIKES_LIST_PLANS: tuple[Plan, ...] = ("plus", "premium")
LIKES_LIST_MAX = 100

# Вернуть пропущенную анкету: бесплатно — нет, Plus — 3 за сутки, Premium — без лимита (None)
REWIND_LIMITS: dict[Plan, int | None] = {"free": 0, "plus": 3, "premium": None}
REWIND_WINDOW = timedelta(days=1)

# Закрытая пати по ссылке — только Premium
PRIVATE_LOBBY_PLANS: tuple[Plan, ...] = ("premium",)

GRANT_DEFAULT = timedelta(days=30)  # срок подписки, выданной админом без указания дней
GRANT_MAX_DAYS = 3650
