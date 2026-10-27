from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import GameOut
from app.db.models import Game

router = APIRouter(tags=["игры"])


@router.get("/games", response_model=list[GameOut])
async def list_games(_user: CurrentUser, session: SessionDep) -> list[Game]:
    """Справочник игр с рангами и ролями — для онбординга и фильтров."""
    games = await session.scalars(
        select(Game)
        .where(Game.is_active)
        .order_by(Game.sort_order)
        .options(selectinload(Game.ranks), selectinload(Game.roles))
    )
    return list(games)
