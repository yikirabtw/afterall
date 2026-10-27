"""Онбординг и редактирование своей анкеты.

Каждый шаг сохраняется отдельно и возвращает свежие данные пользователя (MeOut),
в конце — POST /me/onboarding/complete. Эти же PUT-маршруты потом служат для редактирования профиля.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.me import load_me
from app.api.schemas import AvailabilityIn, BirthDateIn, GamesIn, MeOut, ProfileIn
from app.db.models import Game, Profile, UserAvailability, UserGame
from app.domain.age import age_group_for

router = APIRouter(prefix="/me", tags=["онбординг и анкета"])


def _invalid(code: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=code)


@router.put("/birth-date", response_model=MeOut)
async def set_birth_date(body: BirthDateIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Дата рождения задаётся один раз — иначе можно было бы сменить возрастную группу.

    Исправить её сможет только поддержка. Если человек младше минимального возраста — ничего не сохраняем.
    """
    if user.birth_date is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="birth_date_already_set")
    age_group = age_group_for(body.birth_date)
    if age_group is None:
        raise _invalid("too_young")

    user.birth_date = body.birth_date
    user.age_group = age_group
    await session.commit()
    return await load_me(session, user.id)


@router.put("/profile", response_model=MeOut)
async def save_profile(body: ProfileIn, user: CurrentUser, session: SessionDep) -> MeOut:
    profile = await session.get(Profile, user.id)
    if profile is None:
        profile = Profile(user_id=user.id)
        session.add(profile)
    for field, value in body.model_dump().items():
        setattr(profile, field, value)
    await session.commit()
    return await load_me(session, user.id)


@router.put("/games", response_model=MeOut)
async def save_games(body: GamesIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Заменяет список игр целиком. Ранг и роли должны относиться к своей игре."""
    games = {
        game.id: game
        for game in await session.scalars(
            select(Game)
            .where(Game.id.in_([choice.game_id for choice in body.games]), Game.is_active)
            .options(selectinload(Game.ranks), selectinload(Game.roles))
        )
    }

    new_games = []
    for choice in body.games:
        game = games.get(choice.game_id)
        if game is None:
            raise _invalid("unknown_game")
        if choice.rank_id is not None and choice.rank_id not in {rank.id for rank in game.ranks}:
            raise _invalid("rank_not_in_game")
        roles = [role for role in game.roles if role.id in choice.role_ids]
        if len(roles) != len(choice.role_ids):
            raise _invalid("role_not_in_game")
        new_games.append(
            UserGame(
                user_id=user.id,
                game_id=game.id,
                rank_id=choice.rank_id,
                in_game_nick=choice.in_game_nick,
                is_main=choice.is_main,
                roles=roles,
            )
        )
    # Основная игра нужна для ленты: если не отмечена — берём первую
    if new_games and not any(user_game.is_main for user_game in new_games):
        new_games[0].is_main = True

    await session.execute(delete(UserGame).where(UserGame.user_id == user.id))
    session.add_all(new_games)
    await session.commit()
    return await load_me(session, user.id)


@router.put("/availability", response_model=MeOut)
async def save_availability(body: AvailabilityIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Заменяет расписание целиком. Время — в часовом поясе из анкеты."""
    await session.execute(delete(UserAvailability).where(UserAvailability.user_id == user.id))
    session.add_all(UserAvailability(user_id=user.id, **slot.model_dump()) for slot in body.slots)
    await session.commit()
    return await load_me(session, user.id)


@router.post("/onboarding/complete", response_model=MeOut)
async def complete_onboarding(user: CurrentUser, session: SessionDep) -> MeOut:
    """Завершает онбординг, если заполнено обязательное: дата рождения, анкета, хотя бы одна игра.

    Расписание необязательно. Повторный вызов ничего не меняет.
    """
    if not user.is_onboarded:
        missing = []
        if user.birth_date is None:
            missing.append("birth_date")
        if await session.get(Profile, user.id) is None:
            missing.append("profile")
        if not await session.scalar(select(func.count(UserGame.id)).where(UserGame.user_id == user.id)):
            missing.append("games")
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "onboarding_incomplete", "missing": missing},
            )

        user.onboarded_at = datetime.now(timezone.utc)
        await session.commit()
    return await load_me(session, user.id)
