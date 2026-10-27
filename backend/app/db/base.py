import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Единые имена индексов и ограничений — чтобы миграции Alembic были стабильными
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# BIGINT в Postgres, но INTEGER в SQLite — иначе SQLite не делает автоинкремент
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def str_enum(enum_cls: type[enum.StrEnum]) -> Enum:
    """Enum хранится строкой (VARCHAR), а не нативным типом Postgres — так проще миграции."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
