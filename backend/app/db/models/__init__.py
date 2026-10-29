# Импорт всех моделей в одном месте — чтобы Alembic видел все таблицы
from app.db.models.billing import Subscription
from app.db.models.chat import Chat, ChatMessage, ChatRead
from app.db.models.game import Game, GameRank, GameRole, UserGame, user_game_roles
from app.db.models.lobby import Lobby, LobbyMember
from app.db.models.moderation import ModerationAction, Report, Review
from app.db.models.social import Block, Match, Reaction
from app.db.models.user import Profile, User, UserAvailability, UserPhoto

__all__ = [
    "Block",
    "Chat",
    "ChatMessage",
    "ChatRead",
    "Game",
    "GameRank",
    "GameRole",
    "Lobby",
    "LobbyMember",
    "Match",
    "ModerationAction",
    "Profile",
    "Reaction",
    "Report",
    "Review",
    "Subscription",
    "User",
    "UserAvailability",
    "UserGame",
    "UserPhoto",
    "user_game_roles",
]
