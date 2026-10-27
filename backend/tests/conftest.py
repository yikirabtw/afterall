import httpx
import pytest
from initdata import BOT_TOKEN
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
from app.api.main import create_app
from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys


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
