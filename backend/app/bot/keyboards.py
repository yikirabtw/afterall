from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot import texts

HELP_CALLBACK = "help"


def main_menu(webapp_url: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url:
        builder.button(text=texts.BUTTON_OPEN_APP, web_app=WebAppInfo(url=webapp_url))
    builder.button(text=texts.BUTTON_HELP, callback_data=HELP_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()
