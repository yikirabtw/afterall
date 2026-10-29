from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
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
    """Купленные бусты, ещё не потраченные (пополняет оплата звёздами). По видам: подъём пати дешевле,
    чем «анкета первой», и тратится только на пати."""

    __tablename__ = "boost_credits"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[BoostKind] = mapped_column(str_enum(BoostKind), primary_key=True)
    amount: Mapped[int] = mapped_column(default=0)


class Payment(CreatedAtMixin, Base):
    """Оплата звёздами Telegram — история покупок, основание для возврата."""

    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(String(32))
    stars: Mapped[int]
    telegram_charge_id: Mapped[str] = mapped_column(String(128), unique=True)
    is_recurring: Mapped[bool] = mapped_column(default=False)  # продление подписки, а не первая оплата
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserItem(Base):
    """Купленная или заработанная вещь из косметики (рамка, фон, значок, сцена мэтча, тема)."""

    __tablename__ = "user_items"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(16))  # stars / gift / admin / earned

