from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.db.models  # noqa: F401 — регистрирует все таблицы в Base.metadata
from app.config import settings
from app.db.base import Base
from app.db.session import engine_options, sync_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Адрес базы берём из настроек приложения (backend/.env или переменные окружения), а не из alembic.ini
DATABASE_URL = sync_url(settings.database_url)

# SQLite не умеет большинство ALTER TABLE — Alembic тогда пересоздаёт таблицу целиком
RENDER_AS_BATCH = DATABASE_URL.get_backend_name() == "sqlite"


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=RENDER_AS_BATCH,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    options = engine_options(DATABASE_URL)
    options.pop("pool_pre_ping", None)  # с NullPool проверять нечего — каждое соединение новое
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool, **options)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=RENDER_AS_BATCH,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
