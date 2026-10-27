from datetime import date, datetime
from typing import Annotated, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.db.enums import AgeGroup, LobbyKind, LobbyStatus, LookingFor, MemberStatus, PlayStyle, UserRole
from app.domain.time import as_utc


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _empty_to_none(value: str) -> str | None:
    return value or None


# Необязательный текст: пробелы по краям обрезаются, пустая строка превращается в None
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64), AfterValidator(_empty_to_none)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300), AfterValidator(_empty_to_none)]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200), AfterValidator(_empty_to_none)]
DescriptionText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500), AfterValidator(_empty_to_none)
]
LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
# Время в ответах — всегда с часовым поясом UTC, даже если база вернула его без пояса
UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]

# --- Ввод ---


class BirthDateIn(BaseModel):
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def _plausible(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("birth_date_in_future")
        if value.year < today.year - 100:
            raise ValueError("birth_date_too_old")
        return value


class ProfileIn(BaseModel):
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    bio: LongText | None = None
    has_mic: bool = True
    play_style: PlayStyle = PlayStyle.BALANCED
    looking_for: LookingFor = LookingFor.BOTH
    languages: list[LanguageCode] = Field(
        default_factory=lambda: ["ru"], min_length=1, max_length=5
    )
    country_code: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")] | None = None
    city: ShortText | None = None
    timezone: str = "Europe/Moscow"
    discord_tag: ShortText | None = None
    is_visible: bool = True

    @field_validator("languages")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown_timezone") from None
        return value


class UserGameIn(BaseModel):
    game_id: int
    rank_id: int | None = None
    role_ids: list[int] = Field(default_factory=list, max_length=5)
    in_game_nick: ShortText | None = None
    is_main: bool = False

    @field_validator("role_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class GamesIn(BaseModel):
    """Полный список игр пользователя — заменяет предыдущий."""

    games: list[UserGameIn] = Field(max_length=10)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        game_ids = [game.game_id for game in self.games]
        if len(game_ids) != len(set(game_ids)):
            raise ValueError("duplicate_game")
        if sum(game.is_main for game in self.games) > 1:
            raise ValueError("multiple_main_games")
        return self


class AvailabilitySlotIn(BaseModel):
    weekday: int = Field(ge=0, le=6)  # 0 — пн, 6 — вс
    start_minute: int = Field(ge=0, le=1439)  # минуты от полуночи в часовом поясе пользователя
    end_minute: int = Field(ge=1, le=1440)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start_minute >= self.end_minute:
            raise ValueError("slot_end_before_start")
        return self


class AvailabilityIn(BaseModel):
    """Полное расписание пользователя — заменяет предыдущее. Интервал через полночь — два слота."""

    slots: list[AvailabilitySlotIn] = Field(max_length=28)

    @model_validator(mode="after")
    def _no_overlaps(self) -> Self:
        ordered = sorted(self.slots, key=lambda slot: (slot.weekday, slot.start_minute))
        for previous, current in zip(ordered, ordered[1:]):
            if previous.weekday == current.weekday and current.start_minute < previous.end_minute:
                raise ValueError("overlapping_slots")
        return self


# Куда можно звать людей из пати. Только Telegram и Discord — чтобы не подсовывали фишинговые сайты.
CONTACT_HOSTS = {"t.me", "telegram.me", "discord.gg", "discord.com"}


class LobbyIn(BaseModel):
    kind: LobbyKind = LobbyKind.GAME
    game_id: int | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=80)]
    description: DescriptionText | None = None
    slots_total: int = Field(ge=2, le=20)  # сколько всего человек, включая создателя
    rank_min_id: int | None = None
    rank_max_id: int | None = None
    need_mic: bool = False
    play_style: PlayStyle | None = None  # None — неважно
    language: LanguageCode = "ru"
    starts_at: AwareDatetime | None = None  # None — «прямо сейчас»
    contact_link: str | None = None

    @field_validator("contact_link")
    @classmethod
    def _safe_contact_link(cls, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        parts = urlsplit(value)
        if parts.scheme != "https" or parts.hostname not in CONTACT_HOSTS or len(value) > 256:
            raise ValueError("contact_link_not_allowed")
        if parts.hostname == "discord.com" and not parts.path.startswith("/invite/"):
            raise ValueError("contact_link_not_allowed")
        return value

    @model_validator(mode="after")
    def _game_matches_kind(self) -> Self:
        if self.kind == LobbyKind.GAME and self.game_id is None:
            raise ValueError("game_required")
        if self.kind == LobbyKind.HANGOUT and (self.game_id or self.rank_min_id or self.rank_max_id):
            raise ValueError("hangout_has_no_game")
        return self


class ApplyIn(BaseModel):
    note: NoteText | None = None  # сообщение создателю пати


# --- Вывод ---


class ProfileOut(Schema):
    display_name: str
    bio: str | None
    avatar_url: str | None
    has_mic: bool
    play_style: PlayStyle
    looking_for: LookingFor
    languages: list[str]
    country_code: str | None
    city: str | None
    timezone: str
    discord_tag: str | None
    is_visible: bool
    reputation: int


class UserGameOut(Schema):
    game_id: int
    rank_id: int | None
    role_ids: list[int]
    in_game_nick: str | None
    is_main: bool


class AvailabilitySlotOut(Schema):
    weekday: int
    start_minute: int
    end_minute: int


class MeOut(Schema):
    """Свои данные. Чужие профили будут отдаваться другой схемой — без даты рождения и контактов."""

    id: int
    telegram_id: int
    username: str | None
    first_name: str
    language_code: str | None
    role: UserRole
    birth_date: date | None
    age_group: AgeGroup | None
    is_onboarded: bool
    profile: ProfileOut | None
    games: list[UserGameOut]
    availability: list[AvailabilitySlotOut]


class GameRankOut(Schema):
    id: int
    code: str
    name: str
    tier: int


class GameRoleOut(Schema):
    id: int
    code: str
    name: str


class GameOut(Schema):
    id: int
    slug: str
    name: str
    platforms: list[str]
    max_party_size: int | None
    icon_url: str | None
    ranks: list[GameRankOut]
    roles: list[GameRoleOut]


class LobbyOwnerOut(BaseModel):
    user_id: int
    display_name: str
    avatar_url: str | None
    reputation: int


class LobbyMemberOut(BaseModel):
    """Участник или откликнувшийся. Контакты (username, discord_tag) — только принятым и только принятых."""

    user_id: int
    display_name: str
    avatar_url: str | None
    reputation: int
    has_mic: bool
    rank_id: int | None  # ранг в игре этой пати
    role_ids: list[int]
    status: MemberStatus
    is_owner: bool
    note: str | None
    username: str | None = None
    discord_tag: str | None = None


class LobbyOut(BaseModel):
    id: int
    kind: LobbyKind
    game_id: int | None
    title: str
    description: str | None
    slots_total: int
    slots_taken: int  # принятые, включая создателя
    rank_min_id: int | None
    rank_max_id: int | None
    need_mic: bool
    play_style: PlayStyle | None
    language: str
    starts_at: UtcDatetime | None
    expires_at: UtcDatetime
    status: LobbyStatus
    owner: LobbyOwnerOut
    is_owner: bool
    my_status: MemberStatus | None  # мой отклик или участие; None — не откликался
    contact_link: str | None  # только создателю и принятым


class LobbyDetailOut(LobbyOut):
    # Создатель видит откликнувшихся и принятых, принятый — принятых, остальные — никого
    members: list[LobbyMemberOut]


class LobbyFeedOut(BaseModel):
    items: list[LobbyOut]
    next_cursor: int | None  # передать как cursor, чтобы получить следующую страницу
