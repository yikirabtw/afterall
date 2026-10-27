"""Вебхук Telegram: на сервере обновления от Telegram приходят сюда, а не опрашиваются ботом."""

import hmac
import logging
from typing import Annotated

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    webhook = request.app.state.webhook
    if webhook is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # Telegram присылает секрет, заданный при регистрации вебхука, — так отсекаем поддельные запросы
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "", webhook.secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    update = Update.model_validate(await request.json(), context={"bot": webhook.bot})
    try:
        await webhook.dispatcher.feed_update(webhook.bot, update)
    except Exception:
        # Отвечаем 200 даже при ошибке в хендлере: иначе Telegram будет бесконечно присылать то же обновление
        logger.exception("Ошибка при обработке обновления %s", update.update_id)
    return {"ok": True}
