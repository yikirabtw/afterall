from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
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


def app_link(webapp_url: str, path: str) -> str:
    """Ссылка, по которой мини-приложение сразу откроет нужный экран (читает ?open= при запуске)."""
    separator = "&" if "?" in webapp_url else "?"
    return f"{webapp_url}{separator}open={quote(path, safe='/')}"


def open_app(webapp_url: str, path: str, text: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=app_link(webapp_url, path)))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])

