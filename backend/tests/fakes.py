from collections.abc import AsyncGenerator
from typing import Any

from aiogram.client.session.base import BaseSession
from aiogram.methods import CreateInvoiceLink, SendMessage, TelegramMethod

INVOICE_URL = "https://t.me/$test-invoice"


class RecordingSession(BaseSession):
    """Вместо отправки в Telegram запоминает запросы бота."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if isinstance(method, CreateInvoiceLink):
            return INVOICE_URL
        return True

    async def stream_content(self, *args, **kwargs) -> AsyncGenerator[bytes, None]:
        yield b""

    async def close(self) -> None:
        pass


def outbox(notifier) -> list[SendMessage]:
    """Что отправил бот уведомлений (фикстура notifier) — по порядку."""
    return [request for request in notifier.bot.session.requests if isinstance(request, SendMessage)]
