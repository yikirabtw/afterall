from datetime import date, datetime
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from app.db.enums import (
    AgeGroup,
    BoostKind,
    LobbyKind,
    LobbyStatus,
    LookingFor,
    MemberStatus,
    PlayStyle,
    ReportReason,
    UserRole,
)
from app.domain.age import age_on, search_limits
from app.domain.people import FeedMode
from app.domain.plans import ACTIVE_LOBBY_LIMITS, FEED_PRESETS_MAX, PHOTO_LIMITS, REWIND_LIMITS, Plan
from app.domain.chats import MESSAGE_MAX
from app.domain.time import as_utc, utcnow


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _empty_to_none(value: str) -> str | None:
    return value or None


# Необязательный текст: пробелы по краям обрезаются, пустая строка превращается в None
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64), AfterValidator(_empty_to_none)]
# Описание в анкете — коротко, как подпись к фото
BioText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150), AfterValidator(_empty_to_none)]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200), AfterValidator(_empty_to_none)]
DescriptionText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500), AfterValidator(_empty_to_none)
]
LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
# Время в ответах — всегда с часовым поясом UTC, даже если база вернула его без пояса
UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]

# --- Ввод ---


class FeedPreset(BaseModel):
    """Набор настроек ленты (Premium): режим «Кого ищу» и фильтры — включается одним нажатием."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    mode: FeedMode | None = None
    game_id: int | None = None
    need_mic: bool = False
    play_style: PlayStyle | None = None
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] | None = None


class FeedPresetsIn(BaseModel):
    presets: list[FeedPreset] = Field(max_length=FEED_PRESETS_MAX)


class SearchAgeIn(BaseModel):
    """Возраст поиска в ленте людей. None — до самой рамки (у взрослых сверху — без границы)."""

    age_min: Annotated[int, Field(ge=0, le=150)] | None = None
    age_max: Annotated[int, Field(ge=0, le=150)] | None = None


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
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    bio: BioText | None = None
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
    show_telegram: bool = False  # показывать ли ник в Telegram мэтчам и участникам пати
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
    faceit_elo: int | None = Field(default=None, ge=100, le=5000)  # только для игр с FACEIT (CS2)
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
    is_private: bool = False  # закрытая — только по ссылке-приглашению (Premium)

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
    show_telegram: bool
    is_visible: bool
    search_age_min: int | None  # None — по рамке, см. MeOut.search_age_limits
    search_age_max: int | None
    feed_presets: list[FeedPreset] = []  # наборы настроек ленты (Premium)

    @field_validator("feed_presets", mode="before")
    @classmethod
    def _presets_none_is_empty(cls, value: object) -> object:
        return value or []
    reputation: int


class UserGameOut(Schema):
    game_id: int
    rank_id: int | None
    role_ids: list[int]
    in_game_nick: str | None
    faceit_elo: int | None
    is_main: bool


class AvailabilitySlotOut(Schema):
    weekday: int
    start_minute: int
    end_minute: int


class PhotoOut(Schema):
    id: int
    url: str = ""  # подписанная ссылка; без неё <img> фото не покажет
    width: int  # размеры после обработки — клиенту, чтобы показать фото без обрезки
    height: int

    @model_validator(mode="after")
    def _signed_url(self, info: ValidationInfo) -> Self:
        # Ссылку подписывает тот, кто собирает ответ: передаёт context={"photo_url": функция}
        if not self.url and info.context and "photo_url" in info.context:
            self.url = info.context["photo_url"](self.id)
        return self


class PlanOut(BaseModel):
    """Свой тариф и что он даёт. until — до какого момента действует (у бесплатного None)."""

    plan: Plan = "free"
    until: UtcDatetime | None = None

    @computed_field
    @property
    def photos_max(self) -> int:
        return PHOTO_LIMITS[self.plan]

    @computed_field
    @property
    def active_lobbies_max(self) -> int:
        return ACTIVE_LOBBY_LIMITS[self.plan]

    @computed_field
    @property
    def rewinds_per_day(self) -> int | None:
        """Сколько пропущенных анкет можно вернуть за сутки; None — без лимита, 0 — нельзя."""
        return REWIND_LIMITS[self.plan]


class SearchAgeLimitsOut(BaseModel):
    min: int
    max: int | None  # None — без верхней границы (у взрослых)


class MeOut(Schema):
    """Свои данные. Чужие профили отдаются другой схемой — без даты рождения и контактов."""

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
    photos: list[PhotoOut]  # первое — главное
    games: list[UserGameOut]
    availability: list[AvailabilitySlotOut]
    plan: PlanOut = PlanOut()  # заполняет load_me

    @computed_field
    @property
    def search_age_limits(self) -> SearchAgeLimitsOut | None:
        """Рамки ползунка «Возраст» в ленте людей — дальше них выбрать нельзя."""
        if self.birth_date is None:
            return None
        low, high = search_limits(age_on(self.birth_date, utcnow().date()))
        return SearchAgeLimitsOut(min=low, max=high)


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
    has_faceit: bool
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
    faceit_elo: int | None = None
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
    boosted_until: UtcDatetime | None = None  # поднята в ленте до (буст); на карточке — пометка «поднята»
    is_private: bool = False  # закрытая: в ленте её нет, только по ссылке


class LobbyDetailOut(LobbyOut):
    # Создатель видит откликнувшихся и принятых, принятый — принятых, остальные — никого
    members: list[LobbyMemberOut]
    invite_code: str | None = None  # код приглашения закрытой пати — только создателю


class MetaOut(BaseModel):
    """Что нужно приложению о самом сервисе: ник бота — для ссылок-приглашений (локально его нет)."""

    bot_username: str | None


class LobbyFeedOut(BaseModel):
    items: list[LobbyOut]
    next_cursor: int | None  # передать как cursor, чтобы получить следующую страницу


class PhotoOrderIn(BaseModel):
    """Новый порядок своих фото: первое станет главным."""

    photo_ids: list[int] = Field(min_length=1, max_length=3)


# --- Лента людей ---


class PersonGameOut(Schema):
    game_id: int
    rank_id: int | None
    role_ids: list[int]
    faceit_elo: int | None
    is_main: bool


class PersonOut(BaseModel):
    """Анкета в ленте людей. Без контактов — они открываются только после взаимного лайка."""

    user_id: int
    display_name: str
    age: int | None
    city: str | None
    bio: str | None
    has_mic: bool
    play_style: PlayStyle
    looking_for: LookingFor
    languages: list[str]
    reputation: int
    photos: list[PhotoOut]
    games: list[PersonGameOut]
    # Наша изюминка: насколько человек подходит и почему
    compatibility: int  # 0–100
    common_game_ids: list[int]
    reasons: list[str]
    plan: Plan = "free"  # для значка Plus / Premium у ника
    boosted: bool = False  # анкета поднята бустом — честная пометка на карточке


class ReactIn(BaseModel):
    kind: Literal["like", "skip"]  # «unmatch» ставит только удаление мэтча


class MatchOut(BaseModel):
    """Взаимный лайк. Здесь уже есть контакты."""

    user_id: int
    display_name: str
    age: int | None
    photos: list[PhotoOut]
    main_game_id: int | None
    username: str | None
    discord_tag: str | None
    matched_at: UtcDatetime
    plan: Plan = "free"


class LikesOut(BaseModel):
    """Кто поставил мне ♥, а я ещё не ответил. Число видят все, самих людей — только с Plus и Premium."""

    count: int
    people: list[PersonOut] | None  # None — бесплатный тариф: сервер не отдаёт ни имён, ни фото


class BoostIn(BaseModel):
    kind: BoostKind
    lobby_id: int | None = None  # для kind=lobby — какую из своих пати поднять


class BoostStatusOut(BaseModel):
    """Мои бусты: бесплатные по подписке на этой неделе, купленные, что поднято сейчас."""

    weekly_total: int
    weekly_left: int
    credits: int
    today_left: int
    profile_until: UtcDatetime | None
    lobbies: dict[int, UtcDatetime]  # мои поднятые пати → до какого момента


class ShopProductOut(BaseModel):
    id: str
    kind: str  # plan / boosts / cosmetic
    stars: int  # обычная цена
    price: int  # цена для меня (подписчикам косметика со скидкой)
    owned: bool  # вещь уже есть


class ShopOut(BaseModel):
    payments_enabled: bool  # выключено — витрина «Скоро»
    products: list[ShopProductOut]
    spending_limit: int | None  # лимит трат за 30 дней (13–17 лет); None — без лимита
    spent: int  # потрачено за 30 дней


class InvoiceIn(BaseModel):
    product_id: str


class InvoiceOut(BaseModel):
    url: str  # открыть через Telegram.WebApp.openInvoice


class PaymentOut(BaseModel):
    id: int
    product_id: str
    title: str
    stars: int
    is_recurring: bool
    refunded: bool
    created_at: UtcDatetime


class RewindOut(BaseModel):
    person: PersonOut  # вернулась первой в ленту
    left: int | None  # сколько возвратов ещё осталось за сутки; None — без лимита


class ReactOut(BaseModel):
    match: MatchOut | None  # не None — лайк оказался взаимным


# --- Чаты ---

ChatKind = Literal["direct", "lobby"]  # direct — личный после мэтча, lobby — общий у пати


class MessageIn(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX)]


class ChatMessageOut(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    mine: bool
    body: str
    created_at: UtcDatetime


class ChatHeadOut(BaseModel):
    """О ком или о чём чат: для шапки переписки и строки в списке."""

    kind: ChatKind
    ref: int  # direct — id собеседника, lobby — id пати
    title: str
    photo: PhotoOut | None  # direct — главное фото собеседника
    game_id: int | None  # lobby — игра пати (цвет огонька)
    can_send: bool  # у закончившейся пати чат только для чтения


class ChatSummaryOut(ChatHeadOut):
    last_message: ChatMessageOut | None
    unread: int
    updated_at: UtcDatetime  # для порядка в списке: последнее сообщение или начало переписки


class ChatOut(ChatHeadOut):
    messages: list[ChatMessageOut]  # по возрастанию id
    has_more: bool  # есть ли сообщения старше первого из выданных


# --- Жалобы и блокировки ---


class ReportIn(BaseModel):
    """Жалоба на человека из мэтчей или из общей пати (тогда lobby_id). Жалоба сразу блокирует его для автора."""

    user_id: int
    reason: ReportReason
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    lobby_id: int | None = None


class BlockedOut(BaseModel):
    user_id: int
    display_name: str
    photo: PhotoOut | None
    blocked_at: UtcDatetime

