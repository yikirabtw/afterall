"""Чаты внутри приложения: личные (после мэтча) и общие у пати (для принятых участников).

Ник в Telegram больше не нужен, чтобы договориться: пишут здесь. Незнакомым писать нельзя —
только тем, с кем был взаимный лайк, или участникам своей пати. Заблокированные и забаненные
собеседники из списка пропадают, писать им нельзя.

Новые сообщения клиент забирает сам (опрос раз в несколько секунд) — для бесплатного сервера проще,
чем держать открытые соединения.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import NotifierDep, OnboardedUser, PhotoUrl, SessionDep
from app.api.schemas import ChatKind, ChatMessageOut, ChatOut, ChatSummaryOut, MessageIn, PhotoOut
from app.db.enums import MemberStatus
from app.db.models import Chat, ChatMessage, ChatRead, Lobby, LobbyMember, Match, Profile, User
from app.bot import texts
from app.domain.chats import LOBBY_CHAT_KEEP, NOTIFY_IF_AWAY, PAGE_SIZE, PREVIEW_MAX, RATE_LIMIT, RATE_WINDOW
from app.domain.lobbies import ACTIVE_STATUSES, effective_status
from app.domain.time import as_utc, utcnow
from app.services.notify import Note
from app.services.users import blocked_user_ids, is_ban_active

router = APIRouter(prefix="/chats", tags=["чаты"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "chat_not_found")
UNKNOWN_SENDER = "Участник"


@dataclass
class Access:
    """С кем или в какой пати переписка и что в ней можно."""

    kind: ChatKind
    ref: int
    title: str
    photo: PhotoOut | None
    game_id: int | None
    can_send: bool
    started_at: datetime  # с какого момента переписка возможна — для порядка в списке
    match_id: int | None = None
    lobby_id: int | None = None
    names: dict[int, str] = field(default_factory=dict)  # кто есть кто — подписи сообщений
    recipient_ids: list[int] = field(default_factory=list)  # кому уходит сообщение (кроме меня)


def _main_photo(user: User, photo_url: Callable[[int], str]) -> PhotoOut | None:
    photo = user.photos[0] if user.photos else None
    return PhotoOut(id=photo.id, url=photo_url(photo.id), width=photo.width, height=photo.height) if photo else None


def _name(user: User) -> str:
    return user.profile.display_name if user.profile else user.first_name


async def _my_name(session: AsyncSession, me: User) -> str:
    # Анкета текущего пользователя не подгружена заранее — берём отдельно
    profile = await session.get(Profile, me.id)
    return profile.display_name if profile else me.first_name


async def _direct_access(session: AsyncSession, me: User, other_id: int, photo_url: Callable[[int], str]) -> Access:
    a, b = sorted((me.id, other_id))
    match = await session.scalar(select(Match).where(Match.user_a_id == a, Match.user_b_id == b))
    if match is None or other_id in set(await session.scalars(blocked_user_ids(me.id))):
        raise NOT_FOUND
    other = await session.scalar(
        select(User).where(User.id == other_id).options(selectinload(User.profile), selectinload(User.photos))
    )
    if other is None or is_ban_active(other):
        raise NOT_FOUND
    return Access(
        kind="direct",
        ref=other.id,
        title=_name(other),
        photo=_main_photo(other, photo_url),
        game_id=None,
        can_send=True,
        started_at=match.created_at,
        match_id=match.id,
        names={me.id: await _my_name(session, me), other.id: _name(other)},
        recipient_ids=[other.id],
    )


async def _lobby_access(session: AsyncSession, me: User, lobby_id: int, now: datetime) -> Access:
    lobby = await session.scalar(
        select(Lobby)
        .where(Lobby.id == lobby_id)
        .options(selectinload(Lobby.members).selectinload(LobbyMember.user).selectinload(User.profile))
    )
    mine = next((m for m in lobby.members if m.user_id == me.id), None) if lobby else None
    if lobby is None or mine is None or mine.status != MemberStatus.ACCEPTED:
        raise NOT_FOUND
    return Access(
        kind="lobby",
        ref=lobby.id,
        title=lobby.title,
        photo=None,
        game_id=lobby.game_id,
        can_send=effective_status(lobby.status, lobby.expires_at, now) in ACTIVE_STATUSES,
        started_at=mine.decided_at or lobby.created_at,
        lobby_id=lobby.id,
        # Подписи — и тех, кто уже вышел: их сообщения остаются в истории
        names={m.user_id: _name(m.user) for m in lobby.members},
        recipient_ids=[m.user_id for m in lobby.members if m.status == MemberStatus.ACCEPTED and m.user_id != me.id],
    )


async def _access(
    session: AsyncSession, me: User, kind: ChatKind, ref: int, photo_url: Callable[[int], str]
) -> Access:
    if kind == "direct":
        return await _direct_access(session, me, ref, photo_url)
    return await _lobby_access(session, me, ref, utcnow())


async def _find_chat(session: AsyncSession, access: Access) -> Chat | None:
    if access.match_id is not None:
        return await session.scalar(select(Chat).where(Chat.match_id == access.match_id))
    return await session.scalar(select(Chat).where(Chat.lobby_id == access.lobby_id))


def _message_out(message: ChatMessage, me: User, names: dict[int, str]) -> ChatMessageOut:
    return ChatMessageOut(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=names.get(message.sender_id, UNKNOWN_SENDER),
        mine=message.sender_id == me.id,
        body=message.body,
        created_at=message.created_at,
    )


async def _mark_read(session: AsyncSession, chat_id: int, user_id: int, message_id: int) -> None:
    read = await session.get(ChatRead, (chat_id, user_id))
    if read is None:
        session.add(ChatRead(chat_id=chat_id, user_id=user_id, last_read_id=message_id))
    elif read.last_read_id < message_id:
        read.last_read_id = message_id


@router.get("", response_model=list[ChatSummaryOut])
async def my_chats(user: OnboardedUser, session: SessionDep, photo_url: PhotoUrl) -> list[ChatSummaryOut]:
    """Все переписки: мэтчи и пати, где меня приняли. Свежие сверху."""
    now = utcnow()
    blocked = set(await session.scalars(blocked_user_ids(user.id)))

    accesses: list[Access] = []
    matches = list(await session.scalars(select(Match).where(or_(Match.user_a_id == user.id, Match.user_b_id == user.id))))
    other_ids = {m.user_b_id if m.user_a_id == user.id else m.user_a_id for m in matches} - blocked
    others = {
        other.id: other
        for other in await session.scalars(
            select(User).where(User.id.in_(other_ids)).options(selectinload(User.profile), selectinload(User.photos))
        )
        if not is_ban_active(other, now)
    }
    for match in matches:
        other = others.get(match.user_b_id if match.user_a_id == user.id else match.user_a_id)
        if other is not None:
            accesses.append(
                Access(
                    kind="direct",
                    ref=other.id,
                    title=_name(other),
                    photo=_main_photo(other, photo_url),
                    game_id=None,
                    can_send=True,
                    started_at=match.created_at,
                    match_id=match.id,
                )
            )

    memberships = await session.scalars(
        select(LobbyMember)
        .join(Lobby)
        .where(
            LobbyMember.user_id == user.id,
            LobbyMember.status == MemberStatus.ACCEPTED,
            Lobby.expires_at > now - LOBBY_CHAT_KEEP,
        )
        .options(selectinload(LobbyMember.lobby))
    )
    for member in memberships:
        lobby = member.lobby
        accesses.append(
            Access(
                kind="lobby",
                ref=lobby.id,
                title=lobby.title,
                photo=None,
                game_id=lobby.game_id,
                can_send=effective_status(lobby.status, lobby.expires_at, now) in ACTIVE_STATUSES,
                started_at=member.decided_at or lobby.created_at,
                lobby_id=lobby.id,
            )
        )

    match_ids = [a.match_id for a in accesses if a.match_id is not None]
    lobby_ids = [a.lobby_id for a in accesses if a.lobby_id is not None]
    chats = list(
        await session.scalars(select(Chat).where(or_(Chat.match_id.in_(match_ids), Chat.lobby_id.in_(lobby_ids))))
    )
    chat_ids = [chat.id for chat in chats]
    by_match = {chat.match_id: chat for chat in chats if chat.match_id is not None}
    by_lobby = {chat.lobby_id: chat for chat in chats if chat.lobby_id is not None}

    # Последнее сообщение каждого чата и сколько непрочитанных — двумя запросами на все чаты сразу.
    # Сообщения заблокированных в общих чатах пати не показываем и не считаем
    hidden = blocked_user_ids(user.id)
    last_ids = (
        select(func.max(ChatMessage.id))
        .where(ChatMessage.chat_id.in_(chat_ids), ChatMessage.sender_id.not_in(hidden))
        .group_by(ChatMessage.chat_id)
    )
    last = {
        message.chat_id: message
        for message in await session.scalars(select(ChatMessage).where(ChatMessage.id.in_(last_ids)))
    }
    senders = {
        u.id: _name(u)
        for u in await session.scalars(
            select(User).where(User.id.in_({m.sender_id for m in last.values()})).options(selectinload(User.profile))
        )
    }
    unread = dict(
        (
            await session.execute(
                select(ChatMessage.chat_id, func.count())
                .outerjoin(ChatRead, (ChatRead.chat_id == ChatMessage.chat_id) & (ChatRead.user_id == user.id))
                .where(
                    ChatMessage.chat_id.in_(chat_ids),
                    ChatMessage.sender_id != user.id,
                    ChatMessage.sender_id.not_in(hidden),
                    ChatMessage.id > func.coalesce(ChatRead.last_read_id, 0),
                )
                .group_by(ChatMessage.chat_id)
            )
        ).all()
    )

    result = []
    for access in accesses:
        chat = by_match.get(access.match_id) if access.match_id is not None else by_lobby.get(access.lobby_id)
        message = last.get(chat.id) if chat else None
        preview = None
        if message is not None:
            preview = _message_out(message, user, senders)
            preview.body = preview.body[:PREVIEW_MAX]
        result.append(
            ChatSummaryOut(
                kind=access.kind,
                ref=access.ref,
                title=access.title,
                photo=access.photo,
                game_id=access.game_id,
                can_send=access.can_send,
                last_message=preview,
                unread=unread.get(chat.id, 0) if chat else 0,
                updated_at=message.created_at if message else access.started_at,
            )
        )
    result.sort(key=lambda chat: as_utc(chat.updated_at), reverse=True)
    return result


@router.get("/{kind}/{ref}", response_model=ChatOut)
async def chat_messages(
    kind: ChatKind,
    ref: int,
    user: OnboardedUser,
    session: SessionDep,
    photo_url: PhotoUrl,
    after: Annotated[int | None, Query(ge=0)] = None,
    before: Annotated[int | None, Query(ge=1)] = None,
) -> ChatOut:
    """Переписка. after — только новые (опрос), before — постраничная подгрузка старых. Отмечает прочитанным.
    Сообщений заблокированных (в общем чате пати) не видно."""
    access = await _access(session, user, kind, ref, photo_url)
    chat = await _find_chat(session, access)
    messages: list[ChatMessage] = []
    has_more = False
    if chat is not None:
        query = select(ChatMessage).where(
            ChatMessage.chat_id == chat.id, ChatMessage.sender_id.not_in(blocked_user_ids(user.id))
        )
        if after is not None:
            messages = list(await session.scalars(query.where(ChatMessage.id > after).order_by(ChatMessage.id).limit(PAGE_SIZE)))
        else:
            if before is not None:
                query = query.where(ChatMessage.id < before)
            newest_first = list(await session.scalars(query.order_by(ChatMessage.id.desc()).limit(PAGE_SIZE + 1)))
            has_more = len(newest_first) > PAGE_SIZE
            messages = list(reversed(newest_first[:PAGE_SIZE]))
        if messages and before is None:
            await _mark_read(session, chat.id, user.id, messages[-1].id)
            await session.commit()
    return ChatOut(
        kind=access.kind,
        ref=access.ref,
        title=access.title,
        photo=access.photo,
        game_id=access.game_id,
        can_send=access.can_send,
        messages=[_message_out(m, user, access.names) for m in messages],
        has_more=has_more,
    )


async def _notes_for_message(
    session: AsyncSession, access: Access, chat_id: int, message: ChatMessage, sender: User
) -> list[Note]:
    """Кого позвать в чат через бота: тех, кто сейчас не в приложении и ещё не получил уведомление
    об этом чате с тех пор, как последний раз его читал. Пишут подряд — уведомление одно."""
    if not access.recipient_ids:
        return []
    away = await session.scalars(
        select(User).where(
            User.id.in_(access.recipient_ids),
            User.id.not_in(blocked_user_ids(sender.id)),
            or_(User.last_seen_at.is_(None), User.last_seen_at < message.created_at - NOTIFY_IF_AWAY),
        )
    )
    sender_name = access.names.get(sender.id, UNKNOWN_SENDER)
    notes = []
    for recipient in away:
        if is_ban_active(recipient):
            continue
        read = await session.get(ChatRead, (chat_id, recipient.id))
        if read is None:
            read = ChatRead(chat_id=chat_id, user_id=recipient.id, last_read_id=0)
            session.add(read)
        elif read.notified_id is not None and read.notified_id > read.last_read_id:
            continue  # уже звали и он ещё не заходил
        read.notified_id = message.id
        if access.kind == "direct":
            text, path = texts.notify_direct_message(sender_name, message.body), f"chat/direct/{sender.id}"
        else:
            text = texts.notify_lobby_message(sender_name, access.title, message.body)
            path = f"chat/lobby/{access.ref}"
        notes.append(Note(recipient.telegram_id, text, texts.BUTTON_REPLY, path))
    return notes


@router.post("/{kind}/{ref}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    kind: ChatKind,
    ref: int,
    body: MessageIn,
    user: OnboardedUser,
    session: SessionDep,
    photo_url: PhotoUrl,
    notifier: NotifierDep,
    background: BackgroundTasks,
) -> ChatMessageOut:
    access = await _access(session, user, kind, ref, photo_url)
    if not access.can_send:
        raise HTTPException(status.HTTP_409_CONFLICT, "chat_closed")
    now = utcnow()
    recent = await session.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.sender_id == user.id, ChatMessage.created_at > now - RATE_WINDOW)
    )
    if recent >= RATE_LIMIT:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_messages")

    chat = await _find_chat(session, access)
    if chat is None:
        chat = Chat(match_id=access.match_id, lobby_id=access.lobby_id)
        session.add(chat)
        await session.flush()
    message = ChatMessage(chat_id=chat.id, sender_id=user.id, body=body.body, created_at=now)
    session.add(message)
    chat.last_message_at = now
    await session.flush()
    await _mark_read(session, chat.id, user.id, message.id)
    notes = await _notes_for_message(session, access, chat.id, message, user)
    await session.commit()
    if notes:
        background.add_task(notifier.send, notes)
    return _message_out(message, user, access.names)
