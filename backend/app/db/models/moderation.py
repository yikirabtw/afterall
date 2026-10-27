from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, CreatedAtMixin, TimestampMixin, str_enum
from app.db.enums import ModerationActionKind, ReportReason, ReportStatus, ReviewVerdict


class Review(CreatedAtMixin, Base):
    """Оценка тиммейта после пати. Из них считается репутация."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("lobby_id", "author_id", "target_id"),
        CheckConstraint("author_id <> target_id", name="not_self"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    lobby_id: Mapped[int] = mapped_column(ForeignKey("lobbies.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    verdict: Mapped[ReviewVerdict] = mapped_column(str_enum(ReviewVerdict))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)  # «вовремя», «дружелюбный», «токсик»…
    comment: Mapped[str | None] = mapped_column(String(300))


class Report(TimestampMixin, Base):
    """Жалоба. Жалобы с причиной minor_safety разбираются первыми."""

    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_queue", "status", "reason", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    # Жалоба остаётся в истории, даже если автор удалил аккаунт
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lobby_id: Mapped[int | None] = mapped_column(ForeignKey("lobbies.id", ondelete="SET NULL"))
    reason: Mapped[ReportReason] = mapped_column(str_enum(ReportReason))
    comment: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[ReportStatus] = mapped_column(str_enum(ReportStatus), default=ReportStatus.OPEN)
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolution: Mapped[str | None] = mapped_column(String(500))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModerationAction(CreatedAtMixin, Base):
    """Журнал действий модераторов: кто, кого, за что и до какого времени."""

    __tablename__ = "moderation_actions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id", ondelete="SET NULL"))
    action: Mapped[ModerationActionKind] = mapped_column(str_enum(ModerationActionKind))
    reason: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # для временных мута и бана
