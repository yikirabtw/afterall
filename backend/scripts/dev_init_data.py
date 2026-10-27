"""Тестовый вход для разработки мини-приложения в обычном браузере.

Вне Telegram у страницы нет initData, поэтому скрипт подписывает её сам — токеном бота, как это делает
Telegram, — для тестового пользователя (не вашего аккаунта) и записывает в webapp/.env.development.local.
Этот файл читается только dev-сервером и в продакшен-сборку не попадает. Подпись действует 24 часа.

Из папки backend:
  python -m scripts.dev_init_data          записать вход тестового пользователя
  python -m scripts.dev_init_data --reset  удалить тестового пользователя из базы, чтобы пройти онбординг заново
"""

import argparse
import hashlib
import hmac
import json
import sys
import time
from urllib.parse import urlencode

from sqlalchemy import select

from app.config import BACKEND_DIR, settings
from app.db.models import User
from app.db.session import SessionLocal

TEST_USER = {"id": 1_000_000_001, "first_name": "Тестер", "username": "dev_tester", "language_code": "ru"}
ENV_FILE = BACKEND_DIR.parent / "webapp" / ".env.development.local"


def sign_init_data(user: dict, bot_token: str) -> str:
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "dev",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def reset_test_user() -> None:
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.telegram_id == TEST_USER["id"]))
        if user is None:
            print("Тестового пользователя в базе нет.")
            return
        session.delete(user)
    print("Тестовый пользователь удалён вместе с анкетой и пати.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="удалить тестового пользователя из базы")
    if parser.parse_args().reset:
        reset_test_user()
        return

    if settings.bot_token is None:
        sys.exit("BOT_TOKEN не задан. Добавьте его в backend/.env — см. README.md.")
    init_data = sign_init_data(TEST_USER, settings.bot_token.get_secret_value())
    # Одинарные кавычки — чтобы Vite не пытался подставлять переменные внутри значения
    ENV_FILE.write_text(f"VITE_DEV_INIT_DATA='{init_data}'\n", encoding="utf-8")
    print(f"Вход тестового пользователя записан в {ENV_FILE.name}. Перезапустите dev-сервер мини-приложения.")


if __name__ == "__main__":
    main()
