"""Проверка initData — данных, которые Telegram передаёт мини-приложению при открытии.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from datetime import datetime, timedelta, timezone

from aiogram.utils.web_app import WebAppUser, safe_parse_webapp_init_data


class InitDataError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age: timedelta,
    now: datetime | None = None,
) -> WebAppUser:
    """Возвращает пользователя Telegram, если подпись верна и не устарела, иначе бросает InitDataError."""
    try:
        # Подпись — HMAC от токена бота: подделать её без токена нельзя
        data = safe_parse_webapp_init_data(bot_token, init_data)
    except ValueError:
        raise InitDataError("invalid_init_data") from None

    # Подпись бессрочная, поэтому сами ограничиваем срок — иначе утёкшая initData работала бы вечно
    if (now or datetime.now(timezone.utc)) - data.auth_date > max_age:
        raise InitDataError("init_data_expired")
    if data.user is None:
        raise InitDataError("no_user")
    return data.user
