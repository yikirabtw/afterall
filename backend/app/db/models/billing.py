from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, CreatedAtMixin, str_enum
from app.db.enums import BoostKind, BoostSource, PlanKind, SubscriptionSource


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


class Boost(CreatedAtMixin, Base):
    """Буст: пати или анкета выше в ленте на время. Только сортировка — возраст и блокировки не обходит."""

    __tablename__ = "boosts"
    __table_args__ = (
        Index("ix_boosts_kind_ends", "kind", "ends_at"),
        Index("ix_boosts_user_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[BoostKind] = mapped_column(str_enum(BoostKind))
    lobby_id: Mapped[int | None] = mapped_column(ForeignKey("lobbies.id", ondelete="CASCADE"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[BoostSource] = mapped_column(str_enum(BoostSource))


class BoostCredits(Base):
    """Купленные бусты, ещё не потраченные (пополняется оплатой звёздами)."""

    __tablename__ = "boost_credits"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    amount: Mapped[int] = mapped_column(default=0)

