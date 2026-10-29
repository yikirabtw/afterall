from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    SmallInteger,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, CreatedAtMixin, TimestampMixin, str_enum
from app.db.enums import AgeGroup, LookingFor, PlayStyle, UserRole

if TYPE_CHECKING:
    from app.db.models.game import UserGame


class User(TimestampMixin, Base):
    """Аккаунт: всё, что приходит из Telegram, плюс служебные поля."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(8))
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole), default=UserRole.USER)

    # Возраст: дата рождения (по одному году нельзя точно отделить 17 лет от 18)
    # и вычисленная группа, см. app/domain/age.py.
    # age_group = None, пока человек не прошёл онбординг, — такие не попадают в подбор.
    birth_date: Mapped[date | None] = mapped_column(Date)
    age_group: Mapped[AgeGroup | None] = mapped_column(str_enum(AgeGroup), index=True)

    is_banned: Mapped[bool] = mapped_column(default=False)
    banned_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None при бане — навсегда
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[Profile | None] = relationship(back_populates="user", cascade="all, delete-orphan")
    games: Mapped[list[UserGame]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="UserGame.id"
    )
    availability: Mapped[list[UserAvailability]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by=lambda: (UserAvailability.weekday, UserAvailability.start_minute),
    )
    photos: Mapped[list[UserPhoto]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by=lambda: (UserPhoto.position, UserPhoto.id),
    )

    @property
    def is_onboarded(self) -> bool:
        return self.onboarded_at is not None


class Profile(TimestampMixin, Base):
    """Публичная анкета. Личное фото не обязательно, геолокации нет — только город."""

    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(32))
    bio: Mapped[str | None] = mapped_column(String(300))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    has_mic: Mapped[bool] = mapped_column(default=True)
    play_style: Mapped[PlayStyle] = mapped_column(str_enum(PlayStyle), default=PlayStyle.BALANCED)
    looking_for: Mapped[LookingFor] = mapped_column(str_enum(LookingFor), default=LookingFor.BOTH)
    languages: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["ru"])
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(64))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    discord_tag: Mapped[str | None] = mapped_column(String(64))  # показываем только после мэтча
    # Ник в Telegram видят мэтчи и участники пати, только если человек сам разрешил; иначе — чат в приложении
    show_telegram: Mapped[bool] = mapped_column(default=False, server_default=false())
    is_visible: Mapped[bool] = mapped_column(default=True)  # показывать ли в ленте
    # Возраст поиска в ленте людей («от и до»), взаимный. None — граница по рамкам (domain/age.search_limits)
    search_age_min: Mapped[int | None] = mapped_column(SmallInteger)
    search_age_max: Mapped[int | None] = mapped_column(SmallInteger)
    reputation: Mapped[int] = mapped_column(default=0)  # кэш: положительные минус отрицательные отзывы

    user: Mapped[User] = relationship(back_populates="profile")


class UserAvailability(Base):
    """Когда человек обычно играет. Нужно для подбора и пушей «в твоё время»."""

    __tablename__ = "user_availability"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute", name="time_range"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0 — пн, 6 — вс
    # Минуты от полуночи в часовом поясе пользователя; интервал через полночь — две записи
    start_minute: Mapped[int] = mapped_column(SmallInteger)
    end_minute: Mapped[int] = mapped_column(SmallInteger)

    user: Mapped[User] = relationship(back_populates="availability")


class UserPhoto(CreatedAtMixin, Base):
    """Фото профиля, до трёх; первое по position — главное.

    Хранится в базе уже пережатым JPEG без EXIF (там бывают GPS-координаты) —
    на бесплатном хостинге диск стирается при каждом перезапуске.
    """

    __tablename__ = "user_photos"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
    # deferred: при выдаче списка фото сами байты не нужны — грузим только для GET /photos/{id}
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    width: Mapped[int] = mapped_column(SmallInteger)
    height: Mapped[int] = mapped_column(SmallInteger)

    user: Mapped[User] = relationship(back_populates="photos")
