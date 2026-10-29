from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class AgeGroup(StrEnum):
    """Подбор людей и пати идёт только внутри одной группы."""

    TEEN_13_15 = "13_15"
    TEEN_16_17 = "16_17"
    ADULT = "18_plus"


class PlayStyle(StrEnum):
    CHILL = "chill"
    BALANCED = "balanced"
    TRYHARD = "tryhard"


class LookingFor(StrEnum):
    GAMES = "games"
    HANGOUT = "hangout"
    BOTH = "both"


class LobbyKind(StrEnum):
    GAME = "game"  # пати в конкретную игру
    HANGOUT = "hangout"  # просто провести время: кино, Discord, настолки


class LobbyStatus(StrEnum):
    OPEN = "open"
    FULL = "full"
    STARTED = "started"
    CLOSED = "closed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MemberStatus(StrEnum):
    PENDING = "pending"  # откликнулся, ждёт решения создателя
    ACCEPTED = "accepted"
    DECLINED = "declined"
    LEFT = "left"
    KICKED = "kicked"


class ReactionKind(StrEnum):
    LIKE = "like"
    SKIP = "skip"
    # Человек удалил мэтч: анкета больше не показывается, а повторный лайк с той стороны мэтча не даст.
    # Ставится только сервером при удалении мэтча, из ленты так ответить нельзя.
    UNMATCH = "unmatch"


class MatchSource(StrEnum):
    FEED = "feed"
    LOBBY = "lobby"


class ReviewVerdict(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ReportReason(StrEnum):
    TOXIC = "toxic"
    SPAM = "spam"
    SCAM = "scam"
    INAPPROPRIATE = "inappropriate"
    MINOR_SAFETY = "minor_safety"  # угроза безопасности несовершеннолетнего — в приоритете
    FAKE_PROFILE = "fake_profile"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ModerationActionKind(StrEnum):
    WARN = "warn"
    MUTE = "mute"
    BAN = "ban"
    UNBAN = "unban"
    HIDE_LOBBY = "hide_lobby"


class PlanKind(StrEnum):
    """Платные тарифы. Бесплатный — это отсутствие действующей подписки."""

    PLUS = "plus"
    PREMIUM = "premium"


class SubscriptionSource(StrEnum):
    GRANT = "grant"  # выдал админ (тестерам, в подарок)
    STARS = "stars"  # оплата звёздами Telegram — появится позже


class BoostKind(StrEnum):
    LOBBY = "lobby"  # поднять пати на час
    PROFILE = "profile"  # анкета первой на вечер


class BoostSource(StrEnum):
    WEEKLY = "weekly"  # бесплатный по подписке (Plus — 1 в неделю, Premium — 3)
    CREDIT = "credit"  # купленный заранее (оплата звёздами)

