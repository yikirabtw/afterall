from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.telegram_auth import InitDataError, validate_init_data
from app.db.models import User
from app.services.users import is_ban_active, upsert_telegram_user


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    # Коммитим явно там, где что-то меняем, — чтобы ответ уходил только после сохранения
    async with request.app.state.session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=code, headers={"WWW-Authenticate": "tma"})


async def get_current_user(
    request: Request,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Вход по initData: мини-приложение шлёт в каждом запросе заголовок «Authorization: tma <initData>»."""
    scheme, _, init_data = (authorization or "").partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise _unauthorized("missing_init_data")

    try:
        telegram_user = validate_init_data(
            init_data, request.app.state.bot_token, max_age=request.app.state.init_data_max_age
        )
    except InitDataError as error:
        raise _unauthorized(error.code) from None

    user = await upsert_telegram_user(
        session,
        telegram_id=telegram_user.id,
        first_name=telegram_user.first_name,
        username=telegram_user.username,
        language_code=telegram_user.language_code,
    )
    await session.commit()

    if is_ban_active(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="banned")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_onboarded_user(user: CurrentUser) -> User:
    """Пати и лента — только после онбординга: без возрастной группы нельзя понять, кому что показывать."""
    if not user.is_onboarded or user.age_group is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="onboarding_required")
    return user


OnboardedUser = Annotated[User, Depends(get_onboarded_user)]
