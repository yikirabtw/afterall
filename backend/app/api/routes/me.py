from collections.abc import Callable

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, PhotoUrl, SessionDep
from app.api.schemas import MeOut, PlanOut
from app.db.models import User, UserGame, UserItem
from app.domain.time import utcnow
from app.services.cosmetics import gift_taken_recently
from app.services.plans import plan_of

router = APIRouter(tags=["профиль"])


async def load_me(session: AsyncSession, user_id: int, photo_url: Callable[[int], str]) -> MeOut:
    """Пользователь со всем, что показываем ему самому: анкета, фото, игры, расписание."""
    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.profile),
            selectinload(User.photos),
            selectinload(User.games).selectinload(UserGame.roles),
            selectinload(User.availability),
        )
        # Пользователь уже в сессии (его загрузил вход) — перечитываем связи заново
        .execution_options(populate_existing=True)
    )
    me = MeOut.model_validate(user, context={"photo_url": photo_url})
    plan, until = await plan_of(session, user_id, utcnow())
    me.plan = PlanOut(plan=plan, until=until)
    me.items = sorted(await session.scalars(select(UserItem.item_id).where(UserItem.user_id == user_id)))
    me.gift_available = plan == "premium" and not await gift_taken_recently(session, user_id, utcnow())
    return me


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser, session: SessionDep, photo_url: PhotoUrl) -> MeOut:
    """Вход в мини-приложение: проверяет initData, регистрирует пользователя и возвращает его данные.

    По is_onboarded приложение решает, показать онбординг или главный экран.
    """
    return await load_me(session, user.id, photo_url)
