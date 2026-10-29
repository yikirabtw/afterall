from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, TimestampMixin, str_enum
from app.db.enums import AgeGroup, LobbyKind, LobbyStatus, MemberStatus, PlayStyle

if TYPE_CHECKING:
    from app.db.models.game import Game
    from app.db.models.user import User


class Lobby(TimestampMixin, Base):
    """Заявка «Ищу пати»: в игру или просто провести время."""

    __tablename__ = "lobbies"
    __table_args__ = (
        CheckConstraint("slots_total BETWEEN 2 AND 20", name="slots_range"),
        CheckConstraint("kind = 'hangout' OR game_id IS NOT NULL", name="game_required"),
        # Основной запрос ленты: открытые пати нужной игры и возрастной группы, ещё не истёкшие
        Index("ix_lobbies_feed", "status", "age_group", "game_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[LobbyKind] = mapped_column(str_enum(LobbyKind))
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    slots_total: Mapped[int] = mapped_column(SmallInteger)  # всего человек в пати, включая создателя

    # Требования к участникам; None — неважно
    rank_min_id: Mapped[int | None] = mapped_column(ForeignKey("game_ranks.id", ondelete="SET NULL"))
    rank_max_id: Mapped[int | None] = mapped_column(ForeignKey("game_ranks.id", ondelete="SET NULL"))
    need_mic: Mapped[bool] = mapped_column(default=False)
    play_style: Mapped[PlayStyle | None] = mapped_column(str_enum(PlayStyle))
    language: Mapped[str] = mapped_column(String(8), default="ru")

    # Копируется у создателя: пати видна только своей возрастной группе
    age_group: Mapped[AgeGroup] = mapped_column(str_enum(AgeGroup))

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None — «прямо сейчас»
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # заявка живёт 2–3 часа
    status: Mapped[LobbyStatus] = mapped_column(str_enum(LobbyStatus), default=LobbyStatus.OPEN)
    contact_link: Mapped[str | None] = mapped_column(String(256))  # видна только принятым участникам
    # Закрытая пати (Premium): в ленте её нет, попасть — по ссылке-приглашению с этим кодом
    is_private: Mapped[bool] = mapped_column(default=False, server_default=false())
    invite_code: Mapped[str | None] = mapped_column(String(32), unique=True)

    owner: Mapped[User] = relationship()
    game: Mapped[Game | None] = relationship()
    members: Mapped[list[LobbyMember]] = relationship(back_populates="lobby", cascade="all, delete-orphan")


class LobbyMember(TimestampMixin, Base):
    """Участник пати. Отклик — это запись со статусом pending."""

    __tablename__ = "lobby_members"
    __table_args__ = (
        UniqueConstraint("lobby_id", "user_id"),
        Index("ix_lobby_members_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    lobby_id: Mapped[int] = mapped_column(ForeignKey("lobbies.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_owner: Mapped[bool] = mapped_column(default=False)
    status: Mapped[MemberStatus] = mapped_column(str_enum(MemberStatus), default=MemberStatus.PENDING)
    note: Mapped[str | None] = mapped_column(String(200))  # сообщение к отклику
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lobby: Mapped[Lobby] = relationship(back_populates="members")
    user: Mapped[User] = relationship()
