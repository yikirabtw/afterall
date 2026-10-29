from datetime import datetime, timedelta

from app.db.enums import LobbyStatus
from app.domain.time import as_utc

LOBBY_TTL = timedelta(hours=3)  # заявка живёт 3 часа от начала пати
MAX_START_AHEAD = timedelta(hours=24)  # пати — на сегодня-завтра, а не на месяц вперёд
START_GRACE = timedelta(minutes=5)  # допуск на расхождение часов телефона и сервера
MAX_PENDING_APPLICATIONS = 10

ACTIVE_STATUSES = (LobbyStatus.OPEN, LobbyStatus.FULL)


def effective_status(status: LobbyStatus, expires_at: datetime, now: datetime) -> LobbyStatus:
    """Статус с учётом времени: в базе истёкшая пати может ещё числиться открытой."""
    if status in ACTIVE_STATUSES and as_utc(expires_at) <= now:
        return LobbyStatus.EXPIRED
    return status


def rank_fits(tier: int | None, min_tier: int | None, max_tier: int | None) -> bool:
    """Подходит ли ранг под требования пати. Если требования есть, а ранга не указано — не подходит."""
    if min_tier is None and max_tier is None:
        return True
    if tier is None:
        return False
    return (min_tier is None or tier >= min_tier) and (max_tier is None or tier <= max_tier)
