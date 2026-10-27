from collections.abc import AsyncGenerator
from typing import Any

from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod


class RecordingSession(BaseSession):
    """Вместо отправки в Telegram запоминает запросы бота."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        return True

    async def stream_content(self, *args, **kwargs) -> AsyncGenerator[bytes, None]:
        yield b""

    async def close(self) -> None:
        pass
