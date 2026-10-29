from aiogram import Router

from app.bot.handlers import admin, fallback, help, moderation, payments, start


def build_router() -> Router:
    """Каждый вызов собирает новые роутеры: в aiogram роутер можно подключить только один раз."""
    router = Router(name="root")
    router.include_routers(
        start.create_router(),
        help.create_router(),
        moderation.create_router(),
        admin.create_router(),
        payments.create_router(),
        fallback.create_router(),  # последним: ловит всё, что не поймали остальные
    )
    return router
