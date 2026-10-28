from datetime import date

import httpx
import pytest
from initdata import BOT_TOKEN, auth, make_init_data
from players import Player
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
from app.api.main import create_app
from app.db.base import Base
from app.db.enums import AgeGroup, LookingFor, PlayStyle
from app.db.models import Game, GameRank, GameRole, Profile, User, UserGame
from app.db.session import enable_sqlite_foreign_keys
from app.domain.time import utcnow


@pytest.fixture
def session():
    """Чистая база в памяти на каждый тест."""
    engine = create_engine("sqlite://")
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
async def session_maker():
    """Асинхронная фабрика сессий над чистой базой в памяти (одно соединение на все сессии теста)."""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    enable_sqlite_foreign_keys(engine.sync_engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(session_maker):
    """HTTP-клиент к API поверх тестовой базы, без сети."""
    app = create_app(bot_token=BOT_TOKEN, session_maker=session_maker, cors_origins=["https://app.example"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def world(session_maker) -> dict[str, int]:
    """Игры для тестов: Dota 2 (три ранга, роль), CS2 (один ранг) и выключенная. Возвращает id по коротким именам."""
    async with session_maker.begin() as session:
        dota = Game(slug="dota2", name="Dota 2", platforms=["pc"], max_party_size=5)
        dota.ranks = [
            GameRank(code="herald", name="Рекрут", tier=1),
            GameRank(code="guardian", name="Страж", tier=2),
            GameRank(code="crusader", name="Рыцарь", tier=3),
        ]
        dota.roles = [GameRole(code="carry", name="Керри")]
        cs2 = Game(slug="cs2", name="Counter-Strike 2", platforms=["pc"], max_party_size=5, has_faceit=True)
        cs2.ranks = [GameRank(code="p0", name="Premier до 5 000", tier=1)]
        old = Game(slug="old", name="Старая игра", is_active=False)
        session.add_all([dota, cs2, old])
        await session.flush()
        ids = {"dota": dota.id, "cs2": cs2.id, "old": old.id, "p0": cs2.ranks[0].id}
        ids.update({rank.code: rank.id for rank in dota.ranks})
        return ids


@pytest.fixture
def make_player(session_maker, world):
    """Создаёт пользователя, уже прошедшего онбординг. games — {"dota": "guardian", "cs2": None}, первая — основная."""
    counter = iter(range(1, 1000))

    async def _make(
        age_group: AgeGroup = AgeGroup.TEEN_16_17,
        has_mic: bool = True,
        dota_rank: str | None = "guardian",
        banned: bool = False,
        *,
        games: dict[str, str | None] | None = None,
        play_style: PlayStyle = PlayStyle.BALANCED,
        looking_for: LookingFor = LookingFor.BOTH,
        languages: list[str] | None = None,
        visible: bool = True,
    ) -> Player:
        number = next(counter)
        telegram_id, username = 10_000 + number, f"player{number}"
        games = {"dota": dota_rank} if games is None else games
        async with session_maker.begin() as session:
            user = User(
                telegram_id=telegram_id,
                first_name=username,
                username=username,
                birth_date=date(2009, 1, 1),
                age_group=age_group,
                onboarded_at=utcnow(),
                last_seen_at=utcnow(),
                is_banned=banned,
            )
            user.profile = Profile(
                display_name=f"Игрок {number}",
                has_mic=has_mic,
                discord_tag=f"{username}_dc",
                play_style=play_style,
                looking_for=looking_for,
                languages=languages or ["ru"],
                is_visible=visible,
            )
            user.games = [
                UserGame(game_id=world[game], rank_id=world[rank] if rank else None, is_main=index == 0)
                for index, (game, rank) in enumerate(games.items())
            ]
            session.add(user)
            await session.flush()
            user_id = user.id
        return Player(
            user_id, username, auth(make_init_data(user_id=telegram_id, first_name=username, username=username))
        )

    return _make
