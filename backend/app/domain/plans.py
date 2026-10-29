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

GRANT_DEFAULT = timedelta(days=30)  # срок подписки, выданной админом без указания дней
GRANT_MAX_DAYS = 3650
