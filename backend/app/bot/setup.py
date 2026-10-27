from aiogram import Bot
from aiogram.types import BotCommand, MenuButtonDefault, MenuButtonWebApp, WebAppInfo

from app.bot import texts


async def setup_bot(bot: Bot, webapp_url: str | None) -> None:
    """Команды в меню Telegram и кнопка меню, открывающая мини-приложение."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description=texts.COMMAND_START),
            BotCommand(command="help", description=texts.COMMAND_HELP),
        ]
    )
    if webapp_url:
        menu_button = MenuButtonWebApp(text=texts.MENU_BUTTON, web_app=WebAppInfo(url=webapp_url))
    else:
        menu_button = MenuButtonDefault()
    await bot.set_chat_menu_button(menu_button=menu_button)
