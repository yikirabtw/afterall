from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot import texts

HELP_CALLBACK = "help"
# Решение по жалобе: «mod:<id жалобы>:<ban7|ban|reject>»
MODERATION_PREFIX = "mod"
MODERATION_ACTIONS = ("ban7", "ban", "reject")


def main_menu(webapp_url: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url:
        builder.button(text=texts.BUTTON_OPEN_APP, web_app=WebAppInfo(url=webapp_url))
    builder.button(text=texts.BUTTON_HELP, callback_data=HELP_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()


def moderation_keyboard(report_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action, label in zip(
        MODERATION_ACTIONS, (texts.MOD_BAN_WEEK, texts.MOD_BAN_FOREVER, texts.MOD_REJECT), strict=True
    ):
        builder.button(text=label, callback_data=f"{MODERATION_PREFIX}:{report_id}:{action}")
    builder.adjust(2, 1)
    return builder.as_markup()
