"""Косметика: подарок Premium раз в 30 дней."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserItem
from app.domain.cosmetics import GIFT_PERIOD


async def gift_taken_recently(session: AsyncSession, user_id: int, now: datetime) -> bool:
    taken = await session.scalar(
        select(UserItem.item_id).where(
            UserItem.user_id == user_id, UserItem.source == "gift", UserItem.acquired_at > now - GIFT_PERIOD
        )
    )
    return taken is not None
