"""Подписанные ссылки на фото.

Тег <img> не умеет слать заголовок Authorization, поэтому право смотреть фото проверяется, когда API
выдаёт ссылку (лента людей, профиль, мэтчи), а сама ссылка подписана и живёт несколько часов.
Срок кратен 6 часам — в пределах окна ссылка одна и та же, и браузер берёт фото из кэша.
"""

import hashlib
import hmac
from datetime import datetime

LINK_WINDOW_SECONDS = 6 * 60 * 60


def _signature(photo_id: int, expires: int, secret: str) -> str:
    return hmac.new(secret.encode(), f"{photo_id}:{expires}".encode(), hashlib.sha256).hexdigest()[:32]


def make_photo_url(photo_id: int, secret: str, now: datetime) -> str:
    window_start = int(now.timestamp()) // LINK_WINDOW_SECONDS * LINK_WINDOW_SECONDS
    expires = window_start + 2 * LINK_WINDOW_SECONDS  # живёт от 6 до 12 часов
    return f"/api/photos/{photo_id}?e={expires}&s={_signature(photo_id, expires, secret)}"


def verify_photo_link(photo_id: int, expires: int, signature: str, secret: str, now: datetime) -> bool:
    if expires < now.timestamp():
        return False
    return hmac.compare_digest(signature, _signature(photo_id, expires, secret))
