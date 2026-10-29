import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.routes import (
    boosts,
    chats,
    games,
    health,
    lobbies,
    me,
    onboarding,
    people,
    photos,
    safety,
    shop,
    telegram,
)
from app.bot.dispatcher import build_dispatcher
from app.bot.setup import setup_bot
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.notify import Notifier


@dataclass
class TelegramWebhook:
    """Бот в режиме вебхука: Telegram сам присылает обновления на /telegram/webhook."""

    bot: Bot
    dispatcher: Dispatcher
    secret: str
    url: str | None = None  # куда Telegram шлёт обновления; None — не регистрировать (в тестах)
    webapp_url: str | None = None


def create_app(
    *,
    bot_token: str,
    session_maker: async_sessionmaker[AsyncSession],
    cors_origins: list[str],
    init_data_max_age: timedelta = timedelta(hours=24),
    static_dir: Path | None = None,
    webhook: TelegramWebhook | None = None,
    notifier: Notifier | None = None,
    payments_enabled: bool = False,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if webhook and webhook.url:
            # Регистрируем при каждом старте: бесплатный хостинг засыпает и просыпается
            await setup_bot(webhook.bot, webhook.webapp_url)
            _app.state.bot_username = (await webhook.bot.get_me()).username
            await webhook.bot.set_webhook(
                webhook.url,
                secret_token=webhook.secret,
                allowed_updates=webhook.dispatcher.resolve_used_update_types(),
            )
        yield
        if webhook:
            await webhook.bot.session.close()

    app = FastAPI(title="Teammates API", version="0.1.0", lifespan=lifespan)
    app.state.bot_token = bot_token
    app.state.session_maker = session_maker
    app.state.init_data_max_age = init_data_max_age
    app.state.webhook = webhook
    app.state.bot_username = None  # узнаём у Telegram при старте (только на сервере) — для ссылок-приглашений
    app.state.payments_enabled = payments_enabled
    # Уведомления шлёт тот же бот, что принимает вебхук; без вебхука (локально) — только в лог
    app.state.notifier = notifier or Notifier(webhook.bot if webhook else None, webhook.webapp_url if webhook else None)
    # Ключ подписи ссылок на фото — выводим из токена бота, чтобы не заводить ещё один секрет
    app.state.photo_secret = hashlib.sha256(f"photos:{bot_token}".encode()).hexdigest()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for module in (health, me, onboarding, photos, people, games, lobbies, chats, safety, boosts, shop):
        app.include_router(module.router, prefix="/api")
    app.include_router(telegram.router)
    if static_dir is not None:
        # Последним: всё, что не /api и не вебхук, — файлы мини-приложения
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="webapp")
    return app


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def create_app_from_settings() -> FastAPI:
    if settings.bot_token is None:
        raise RuntimeError("BOT_TOKEN не задан: без него нельзя проверить вход из мини-приложения.")
    token = settings.bot_token.get_secret_value()

    static_dir = settings.static_dir if settings.static_dir and settings.static_dir.is_dir() else None
    # Если мини-приложение отдаём сами — его адрес совпадает с адресом сервиса
    webapp_url = settings.webapp_url or (settings.public_url if static_dir else None)

    cors_origins = list(settings.cors_origins)
    if webapp_url:
        cors_origins.append(_origin(webapp_url))

    admin_ids = frozenset(settings.admin_telegram_ids)
    webhook = None
    if settings.public_url:
        secret = (
            settings.webhook_secret.get_secret_value()
            if settings.webhook_secret
            # Telegram разрешает в секрете только буквы, цифры, _ и - — hex подходит
            else hashlib.sha256(f"webhook:{token}".encode()).hexdigest()
        )
        webhook = TelegramWebhook(
            bot=Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)),
            dispatcher=build_dispatcher(AsyncSessionLocal, webapp_url, admin_ids),
            secret=secret,
            url=f"{settings.public_url.rstrip('/')}/telegram/webhook",
            webapp_url=webapp_url,
        )

    return create_app(
        bot_token=token,
        session_maker=AsyncSessionLocal,
        cors_origins=cors_origins,
        init_data_max_age=timedelta(hours=settings.init_data_max_age_hours),
        static_dir=static_dir,
        webhook=webhook,
        notifier=Notifier(webhook.bot if webhook else None, webapp_url, admin_ids),
        payments_enabled=settings.payments_enabled,
    )
