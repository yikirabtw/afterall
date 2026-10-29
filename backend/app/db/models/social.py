from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, CreatedAtMixin, str_enum
from app.db.enums import MatchSource, ReactionKind


class Reaction(CreatedAtMixin, Base):
    """Лайк или пропуск анкеты в ленте."""

    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id"),
        CheckConstraint("from_user_id <> to_user_id", name="not_self"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[ReactionKind] = mapped_column(str_enum(ReactionKind))
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"))  # в какой игре искали


class Match(CreatedAtMixin, Base):
    """Взаимный интерес. Только после мэтча видны контакты (Telegram, Discord)."""

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id"),
        # Одна запись на пару: меньший id всегда в user_a_id
        CheckConstraint("user_a_id < user_b_id", name="ordered_pair"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[MatchSource] = mapped_column(str_enum(MatchSource))
    lobby_id: Mapped[int | None] = mapped_column(ForeignKey("lobbies.id", ondelete="SET NULL"))


class Block(CreatedAtMixin, Base):
    """Заблокированный пользователь больше не видит блокирующего и не может откликнуться на его пати."""

    __tablename__ = "blocks"
    __table_args__ = (CheckConstraint("blocker_id <> blocked_id", name="not_self"),)

    blocker_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)


class Rewind(CreatedAtMixin, Base):
    """Возврат пропущенной анкеты (Plus — 3 в сутки, Premium — без лимита). Журнал — чтобы считать лимит."""

    __tablename__ = "rewinds"
    __table_args__ = (Index("ix_rewinds_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

