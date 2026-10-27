"""Локальный запуск бота (long polling). Из папки backend:  python -m app.bot

На сервере бот работает иначе — через вебхук внутри API (см. app/api/main.py).
"""

import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.dispatcher import build_dispatcher
from app.bot.setup import setup_bot
from app.config import settings
from app.db.session import AsyncSessionLocal


async def main(token: str) -> None:
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    webhook = await bot.get_webhook_info()
    if webhook.url:
        # Иначе delete_webhook ниже молча увёл бы бота с сервера
        await bot.session.close()
        raise SystemExit(
            f"Этот бот уже работает на сервере через вебхук ({webhook.url}).\n"
            "Для локальной разработки заведите отдельного тестового бота в @BotFather "
            "и укажите его токен в backend/.env."
        )

    dispatcher = build_dispatcher(AsyncSessionLocal, settings.webapp_url)
    await setup_bot(bot, settings.webapp_url)
    await bot.delete_webhook(drop_pending_updates=True)  # не отвечаем на то, что накопилось, пока бот был выключен
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if settings.bot_token is None:
        sys.exit("BOT_TOKEN не задан. Добавьте его в backend/.env — см. README.md.")

    # Асинхронный драйвер PostgreSQL не работает со стандартным циклом событий Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(settings.bot_token.get_secret_value()), loop_factory=loop_factory)
