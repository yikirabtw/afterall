"""Подпись initData для тестов — независимо от кода приложения, по алгоритму из документации Telegram."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

BOT_TOKEN = "42:TEST"
USER_ID = 100


def sign(fields: dict[str, str], token: str = BOT_TOKEN) -> str:
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": signature})


def make_init_data(
    first_name: str = "Аня",
    auth_date: datetime | None = None,
    token: str = BOT_TOKEN,
    user_id: int = USER_ID,
    username: str = "anya",
) -> str:
    user = {"id": user_id, "first_name": first_name, "username": username, "language_code": "ru"}
    auth_date = auth_date or datetime.now(timezone.utc)
    return sign(
        {
            "query_id": "AAHtest",
            "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
            "auth_date": str(int(auth_date.timestamp())),
        },
        token,
    )


def auth(init_data: str | None = None) -> dict[str, str]:
    return {"Authorization": f"tma {init_data or make_init_data()}"}
