from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import build_router
from app.bot.middlewares import DbSessionMiddleware, UserMiddleware


def build_dispatcher(
    session_maker: async_sessionmaker[AsyncSession],
    webapp_url: str | None,
    admin_ids: frozenset[int] = frozenset(),
) -> Dispatcher:
    # webapp_url и admin_ids попадают в хендлеры как аргументы — так их проще тестировать
    dispatcher = Dispatcher(webapp_url=webapp_url, admin_ids=admin_ids)
    dispatcher.update.middleware(DbSessionMiddleware(session_maker))
    dispatcher.update.middleware(UserMiddleware())  # после DbSessionMiddleware: ему нужна сессия
    dispatcher.include_router(build_router())
    return dispatcher
