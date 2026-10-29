from fastapi import APIRouter, Request

from app.api.schemas import MetaOut

router = APIRouter(tags=["служебное"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Проверка, что API запущен. Без авторизации."""
    return {"status": "ok"}


@router.get("/meta", response_model=MetaOut)
async def meta(request: Request) -> MetaOut:
    """Ник бота — приложению для ссылок-приглашений. Без авторизации: это не секрет."""
    return MetaOut(bot_username=request.app.state.bot_username)
