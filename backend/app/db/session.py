from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    """SQLite по умолчанию игнорирует внешние ключи."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def sync_url(url: str) -> URL:
    """Адрес базы с нашим драйвером. Хостинги (Neon, Render) выдают его как postgres:// или postgresql://."""
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        return parsed.set(drivername="postgresql+psycopg")
    return parsed


def async_url(url: str) -> URL:
    """Тот же адрес базы, но с асинхронным драйвером."""
    parsed = sync_url(url)
    if parsed.drivername == "sqlite":
        return parsed.set(drivername="sqlite+aiosqlite")
    return parsed  # psycopg умеет и синхронно, и асинхронно


def engine_options(url: URL) -> dict:
    if url.get_backend_name() != "postgresql":
        return {}
    return {
        # Бесплатный Neon усыпляет базу без запросов — проверяем соединение перед использованием
        "pool_pre_ping": True,
        # Без подготовленных запросов: с ними ломается пул соединений Neon (PgBouncer)
        "connect_args": {"prepare_threshold": None},
    }


# Синхронное подключение — для скриптов и миграций
_sync_url = sync_url(settings.database_url)
engine = create_engine(_sync_url, **engine_options(_sync_url))
enable_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

# Асинхронное подключение — для бота и API
_async_url = async_url(settings.database_url)
async_engine = create_async_engine(_async_url, **engine_options(_async_url))
enable_sqlite_foreign_keys(async_engine.sync_engine)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
