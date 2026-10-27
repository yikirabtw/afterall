"""Всё, что нужно для работы на хостинге: вебхук бота, раздача мини-приложения, адрес базы."""

from datetime import datetime, timezone

import httpx
import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendMessage
from fakes import RecordingSession
from initdata import BOT_TOKEN, auth
from sqlalchemy import select

from app.api.main import TelegramWebhook, create_app
from app.bot.dispatcher import build_dispatcher
from app.db.models import User
from app.db.session import async_url, sync_url

SECRET = "test-secret"


def start_update(update_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "chat": {"id": 100, "type": "private"},
            "from": {"id": 100, "is_bot": False, "first_name": "Аня"},
            "text": "/start",
        },
    }


@pytest.fixture
def bot() -> Bot:
    return Bot("42:TEST", session=RecordingSession())


@pytest.fixture
async def webhook_client(session_maker, bot, tmp_path):
    (tmp_path / "index.html").write_text("<title>afterall</title>", encoding="utf-8")
    app = create_app(
        bot_token=BOT_TOKEN,
        session_maker=session_maker,
        cors_origins=[],
        static_dir=tmp_path,
        webhook=TelegramWebhook(bot=bot, dispatcher=build_dispatcher(session_maker, None), secret=SECRET),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_webhook_handles_update(webhook_client, bot, session_maker):
    response = await webhook_client.post(
        "/telegram/webhook", json=start_update(), headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
    )

    assert response.json() == {"ok": True}
    [reply] = [request for request in bot.session.requests if isinstance(request, SendMessage)]
    assert reply.text.startswith("Привет, Аня!")
    async with session_maker() as session:
        assert (await session.scalar(select(User))).telegram_id == 100


@pytest.mark.parametrize("headers", [{}, {"X-Telegram-Bot-Api-Secret-Token": "wrong"}])
async def test_webhook_rejects_requests_without_secret(webhook_client, bot, headers):
    response = await webhook_client.post("/telegram/webhook", json=start_update(), headers=headers)

    assert response.status_code == 403
    assert bot.session.requests == []


async def test_webhook_answers_ok_even_if_handler_fails(session_maker, bot):
    """Иначе Telegram будет бесконечно присылать обновление, на котором бот падает."""
    dispatcher = Dispatcher()

    @dispatcher.message()
    async def broken(message):
        raise RuntimeError("boom")

    app = create_app(
        bot_token=BOT_TOKEN,
        session_maker=session_maker,
        cors_origins=[],
        webhook=TelegramWebhook(bot=bot, dispatcher=dispatcher, secret=SECRET),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(
            "/telegram/webhook", json=start_update(), headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


async def test_webhook_is_off_without_config(client):
    response = await client.post("/telegram/webhook", json=start_update())
    assert response.status_code == 404


async def test_webapp_is_served_next_to_api(webhook_client):
    page = await webhook_client.get("/")
    assert page.status_code == 200
    assert "<title>afterall</title>" in page.text

    assert (await webhook_client.get("/api/health")).json() == {"status": "ok"}
    assert (await webhook_client.get("/api/me", headers=auth())).status_code == 200


@pytest.mark.parametrize(
    ("url", "sync_driver", "async_driver"),
    [
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg", "postgresql+psycopg"),
        ("postgres://u:p@host/db", "postgresql+psycopg", "postgresql+psycopg"),
        ("sqlite:///dev.db", "sqlite", "sqlite+aiosqlite"),
    ],
)
def test_database_url_drivers(url, sync_driver, async_driver):
    assert sync_url(url).drivername == sync_driver
    assert async_url(url).drivername == async_driver
    assert sync_url(url).query == async_url(url).query  # sslmode и прочие параметры не теряются
