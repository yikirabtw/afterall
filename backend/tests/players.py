from dataclasses import dataclass


@dataclass
class Player:
    """Тестовый пользователь, уже прошедший онбординг: его id в базе, ник и заголовок входа."""

    id: int
    username: str
    headers: dict[str, str]
    telegram_id: int = 0
