from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """SQLite возвращает время без часового пояса. Храним всегда UTC — его и подставляем."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
