"""Разбор жалоб прямо в боте: модератору приходит карточка жалобы с кнопками (её шлёт API, routes/safety.py).

Права проверяются здесь, на сервере: кнопку может нажать кто угодно, кому переслали сообщение.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards import MODERATION_ACTIONS, MODERATION_PREFIX
from app.db.models import Report, User
from app.domain.time import utcnow
from app.services.moderation import OPEN_STATUSES, can_moderate, decide_report


async def decide(callback: CallbackQuery, session: AsyncSession, user: User, admin_ids: frozenset[int]) -> None:
    if not can_moderate(user, admin_ids):
        await callback.answer(texts.MOD_NO_RIGHTS, show_alert=True)
        return

    _, report_id, action = callback.data.split(":")
    report = await session.get(Report, int(report_id))
    if report is None or report.status not in OPEN_STATUSES or action not in MODERATION_ACTIONS:
        await callback.answer(texts.MOD_ALREADY_DONE, show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await decide_report(session, report, action, user, utcnow())
    if callback.message:
        # Решение дописываем в саму карточку — у остальных модераторов кнопки тоже станут неактуальны
        await callback.message.edit_text(
            callback.message.html_text + texts.mod_decision(action, user.first_name), reply_markup=None
        )
    await callback.answer()


def create_router() -> Router:
    router = Router(name="moderation")
    router.callback_query.register(decide, F.data.startswith(f"{MODERATION_PREFIX}:"))
    return router
