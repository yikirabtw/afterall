from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, CreatedAtMixin, str_enum
from app.db.enums import PlanKind, SubscriptionSource


class Subscription(CreatedAtMixin, Base):
    """Подписка Plus или Premium на срок. Действует, пока starts_at <= сейчас < ends_at.

    Продление — новая запись или сдвиг ends_at; история остаётся — пригодится для оплат и споров.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_user_ends", "user_id", "ends_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan: Mapped[PlanKind] = mapped_column(str_enum(PlanKind))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[SubscriptionSource] = mapped_column(str_enum(SubscriptionSource))
    granted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
