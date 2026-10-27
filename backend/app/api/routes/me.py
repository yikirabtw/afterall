from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import MeOut
from app.db.models import User, UserGame

router = APIRouter(tags=["профиль"])


async def load_me(session: AsyncSession, user_id: int) -> MeOut:
    """Пользователь со всем, что показываем ему самому: анкета, игры, расписание."""
    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.profile),
            selectinload(User.games).selectinload(UserGame.roles),
            selectinload(User.availability),
        )
        # Пользователь уже в сессии (его загрузил вход) — перечитываем связи заново
        .execution_options(populate_existing=True)
    )
    return MeOut.model_validate(user)


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser, session: SessionDep) -> MeOut:
    """Вход в мини-приложение: проверяет initData, регистрирует пользователя и возвращает его данные.

    По is_onboarded приложение решает, показать онбординг или главный экран.
    """
    return await load_me(session, user.id)
