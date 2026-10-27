from fastapi import APIRouter

router = APIRouter(tags=["служебное"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Проверка, что API запущен. Без авторизации."""
    return {"status": "ok"}
