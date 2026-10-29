"""Бусты: поднять свою пати на час или анкету на вечер. Только сортировка — возраст и блокировки не обходит.

Сначала тратятся бесплатные по подписке (Plus — 1 в неделю, Premium — 3), потом купленные. Не больше трёх
в сутки и одного действующего на пати или анкету — чтобы лента не превращалась в рекламу.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OnboardedUser, SessionDep
from app.api.schemas import BoostIn, BoostStatusOut
from app.db.enums import BoostKind, BoostSource, LobbyStatus
from app.db.models import Boost, BoostCredits, Lobby, User
from app.domain.boosts import DAILY_MAX, DURATION
from app.domain.time import as_utc, utcnow
from app.services.boosts import allowance, boosted_lobbies, boosted_profiles
from app.services.plans import plan_of

router = APIRouter(prefix="/boosts", tags=["бусты"])


async def _status(session: AsyncSession, user: User, now) -> BoostStatusOut:
    plan, _ = await plan_of(session, user.id, now)
    left = await allowance(session, user.id, plan, now)
    mine = select(Lobby.id).where(Lobby.owner_id == user.id)
    return BoostStatusOut(
        weekly_total=left.weekly_total,
        weekly_left=left.weekly_left,
        credits=left.credits,
        today_left=max(0, DAILY_MAX - left.today),
        profile_until=(await boosted_profiles(session, [user.id], now)).get(user.id),
        lobbies=await boosted_lobbies(session, now, await session.scalars(mine)),
    )


@router.get("", response_model=BoostStatusOut)
async def my_boosts(user: OnboardedUser, session: SessionDep) -> BoostStatusOut:
    return await _status(session, user, utcnow())


@router.post("", response_model=BoostStatusOut)
async def use_boost(body: BoostIn, user: OnboardedUser, session: SessionDep) -> BoostStatusOut:
    now = utcnow()
    if body.kind == BoostKind.LOBBY:
        lobby = await session.get(Lobby, body.lobby_id) if body.lobby_id is not None else None
        if lobby is None or lobby.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="lobby_not_found")
        if lobby.status != LobbyStatus.OPEN or as_utc(lobby.expires_at) <= now:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="lobby_not_active")
        already = (await boosted_lobbies(session, now, [lobby.id])).get(lobby.id)
    else:
        already = (await boosted_profiles(session, [user.id], now)).get(user.id)
    if already is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="boost_already_active")

    plan, _ = await plan_of(session, user.id, now)
    left = await allowance(session, user.id, plan, now)
    if left.today >= DAILY_MAX:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="boosts_daily_limit")
    if left.weekly_left > 0:
        source = BoostSource.WEEKLY
    elif left.credits > 0:
        source = BoostSource.CREDIT
        credits = await session.get(BoostCredits, user.id)
        credits.amount -= 1
    else:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail="boost_needs_purchase")

    session.add(
        Boost(
            user_id=user.id,
            kind=body.kind,
            lobby_id=body.lobby_id if body.kind == BoostKind.LOBBY else None,
            starts_at=now,
            ends_at=now + DURATION[body.kind],
            source=source,
            created_at=now,
        )
    )
    await session.commit()
    return await _status(session, user, now)
