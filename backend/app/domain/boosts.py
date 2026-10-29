"""Бусты: сколько длятся, сколько можно, сколько бесплатно по тарифу (docs/ROADMAP.md → «Монетизация»)."""

from datetime import timedelta

from app.db.enums import BoostKind
from app.domain.plans import Plan

DURATION = {BoostKind.LOBBY: timedelta(hours=1), BoostKind.PROFILE: timedelta(hours=6)}
DAILY_MAX = 3  # бустов в сутки с одного аккаунта — чтобы лента не превращалась в рекламу
DAY = timedelta(days=1)
WEEK = timedelta(days=7)
WEEKLY_FREE: dict[Plan, int] = {"free": 0, "plus": 1, "premium": 3}
