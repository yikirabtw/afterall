"""Запуск API. Из папки backend:  python -m app.api   (документация — /docs)"""

import sys

import uvicorn

from app.config import settings

if __name__ == "__main__":
    if settings.bot_token is None:
        sys.exit("BOT_TOKEN не задан. Добавьте его в backend/.env — см. README.md.")
    uvicorn.run("app.api.main:create_app_from_settings", factory=True, host=settings.api_host, port=settings.api_port)
