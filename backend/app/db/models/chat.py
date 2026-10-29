from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, CreatedAtMixin


class Chat(CreatedAtMixin, Base):
    """Переписка внутри приложения: личная — после мэтча, общая — у пати для её принятых участников.

    Ник в Telegram больше не нужен, чтобы договориться: пишут здесь. Запись создаётся с первым сообщением.
    """

    __tablename__ = "chats"
    __table_args__ = (CheckConstraint("(match_id IS NULL) <> (lobby_id IS NULL)", name="one_owner"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), unique=True)
    lobby_id: Mapped[int | None] = mapped_column(ForeignKey("lobbies.id", ondelete="CASCADE"), unique=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatMessage(CreatedAtMixin, Base):
    """Сообщение. Только текст; фото и голосовые — позже, с модерацией."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        # Сообщения чата по порядку и «новые после такого-то» — основной запрос
        Index("ix_chat_messages_chat_order", "chat_id", "id"),
        # Ограничение частоты: сколько человек написал за последнюю минуту
        Index("ix_chat_messages_sender_time", "sender_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(String(1000))


class ChatRead(Base):
    """До какого сообщения человек прочитал чат — для счётчика непрочитанных."""

    __tablename__ = "chat_reads"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_read_id: Mapped[int] = mapped_column(BigInteger, default=0)
    # О каком сообщении последний раз прислали уведомление в боте. Пока человек не прочитал чат, второе не шлём
    notified_id: Mapped[int | None] = mapped_column(BigInteger)
