from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, ForeignKey, SmallInteger, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class Game(Base):
    """Справочник игр. Заполняется скриптом scripts/seed_games.py."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    platforms: Mapped[list[str]] = mapped_column(JSON, default=list)  # pc, mobile, console
    max_party_size: Mapped[int | None] = mapped_column(SmallInteger)  # None — без ограничения
    icon_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    ranks: Mapped[list[GameRank]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="GameRank.tier"
    )
    roles: Mapped[list[GameRole]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="GameRole.sort_order"
    )


class GameRank(Base):
    __tablename__ = "game_ranks"
    __table_args__ = (
        UniqueConstraint("game_id", "code"),
        UniqueConstraint("game_id", "tier"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    tier: Mapped[int] = mapped_column(SmallInteger)  # чем больше, тем выше ранг; нужно для «близкого ранга»

    game: Mapped[Game] = relationship(back_populates="ranks")


class GameRole(Base):
    __tablename__ = "game_roles"
    __table_args__ = (UniqueConstraint("game_id", "code"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(default=0)

    game: Mapped[Game] = relationship(back_populates="roles")


user_game_roles = Table(
    "user_game_roles",
    Base.metadata,
    Column("user_game_id", ForeignKey("user_games.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("game_roles.id", ondelete="CASCADE"), primary_key=True),
)


class UserGame(TimestampMixin, Base):
    """Игра в профиле человека: ранг и роли.

    Что rank и roles принадлежат той же игре, проверяет сервисный слой.
    """

    __tablename__ = "user_games"
    __table_args__ = (UniqueConstraint("user_id", "game_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    rank_id: Mapped[int | None] = mapped_column(ForeignKey("game_ranks.id", ondelete="SET NULL"))
    in_game_nick: Mapped[str | None] = mapped_column(String(64))
    is_main: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship(back_populates="games")
    game: Mapped[Game] = relationship()
    rank: Mapped[GameRank | None] = relationship()
    roles: Mapped[list[GameRole]] = relationship(secondary=user_game_roles, order_by="GameRole.sort_order")

    @property
    def role_ids(self) -> list[int]:
        return [role.id for role in self.roles]
