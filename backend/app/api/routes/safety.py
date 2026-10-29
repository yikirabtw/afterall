"""Жалобы и блокировки.

Блокировка — взаимная невидимость: лента, мэтчи и чаты друг друга пропадают (services/users.blocked_user_ids),
сам мэтч остаётся — после разблокировки всё вернётся. Жалоба (решение пользователя) сразу же блокирует
человека для автора и уходит модераторам в бот с кнопками бана (bot/handlers/moderation.py).
Пожаловаться можно только на того, с кем есть мэтч или общая пати, — на случайных людей по id нельзя.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import NotifierDep, OnboardedUser, PhotoUrl, SessionDep
from app.api.schemas import BlockedOut, PhotoOut, ReportIn
from app.bot import texts
from app.bot.keyboards import moderation_keyboard
from app.db.models import Block, Chat, ChatMessage, LobbyMember, Match, Profile, Report, User
from app.domain.age import age_on
from app.domain.safety import REPORT_CONTEXT_MESSAGES, REPORTS_PER_DAY, REPORTS_WINDOW
from app.domain.time import utcnow
from app.services.moderation import OPEN_STATUSES
from app.services.notify import Note, moderator_telegram_ids

router = APIRouter(tags=["жалобы и блокировки"])


def _done() -> Response:
    # Каждый раз новый объект: FastAPI вешает на возвращённый Response фоновые задачи запроса,
    # и общий на модуль ответ повторял бы чужие уведомления
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _error(code: str, status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT) -> HTTPException:
    return HTTPException(status_code, detail=code)


async def _other_user(session: AsyncSession, me: User, user_id: int) -> User:
    if user_id == me.id:
        raise _error("cannot_target_self")
    user = await session.scalar(select(User).where(User.id == user_id).options(selectinload(User.profile)))
    if user is None:
        raise _error("user_not_found", status.HTTP_404_NOT_FOUND)
    return user


async def _block(session: AsyncSession, me: User, other_id: int) -> None:
    if await session.get(Block, (me.id, other_id)) is None:
        session.add(Block(blocker_id=me.id, blocked_id=other_id))


# --- Блокировки ---


@router.get("/blocks", response_model=list[BlockedOut])
async def my_blocks(user: OnboardedUser, session: SessionDep, photo_url: PhotoUrl) -> list[BlockedOut]:
    """Кого я заблокировал, новые сверху, — чтобы можно было передумать."""
    rows = await session.execute(
        select(Block, User)
        .join(User, User.id == Block.blocked_id)
        .where(Block.blocker_id == user.id)
        .options(selectinload(User.profile), selectinload(User.photos))
        .order_by(Block.created_at.desc())
    )
    result = []
    for block, other in rows:
        photo = other.photos[0] if other.photos else None
        result.append(
            BlockedOut(
                user_id=other.id,
                display_name=other.profile.display_name if other.profile else other.first_name,
                photo=PhotoOut(id=photo.id, url=photo_url(photo.id), width=photo.width, height=photo.height)
                if photo
                else None,
                blocked_at=block.created_at,
            )
        )
    return result


@router.post("/blocks/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def block_user(user_id: int, user: OnboardedUser, session: SessionDep) -> Response:
    await _other_user(session, user, user_id)
    await _block(session, user, user_id)
    await session.commit()
    return _done()


@router.delete("/blocks/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(user_id: int, user: OnboardedUser, session: SessionDep) -> Response:
    block = await session.get(Block, (user.id, user_id))
    if block is not None:
        await session.delete(block)
        await session.commit()
    return _done()


# --- Жалобы ---


async def _match(session: AsyncSession, a: int, b: int) -> Match | None:
    low, high = sorted((a, b))
    return await session.scalar(select(Match).where(Match.user_a_id == low, Match.user_b_id == high))


async def _both_in_lobby(session: AsyncSession, lobby_id: int, a: int, b: int) -> bool:
    members = await session.scalar(
        select(func.count(LobbyMember.id)).where(LobbyMember.lobby_id == lobby_id, LobbyMember.user_id.in_((a, b)))
    )
    return members == 2


async def _context(
    session: AsyncSession, match: Match | None, body: ReportIn, names: dict[int, str]
) -> list[tuple[str, str]]:
    """Последние сообщения — модератору, чтобы было видно, что произошло: вся личная переписка
    или сообщения нарушителя в чате пати."""
    if body.lobby_id is not None:
        where = and_(Chat.lobby_id == body.lobby_id, ChatMessage.sender_id == body.user_id)
    elif match is not None:
        where = Chat.match_id == match.id
    else:
        return []
    messages = list(
        await session.scalars(
            select(ChatMessage)
            .join(Chat, Chat.id == ChatMessage.chat_id)
            .where(where)
            .order_by(ChatMessage.id.desc())
            .limit(REPORT_CONTEXT_MESSAGES)
        )
    )
    return [(names.get(message.sender_id, "?"), message.body) for message in reversed(messages)]


def _label(user: User, profile: Profile | None, today) -> str:
    name = profile.display_name if profile else user.first_name
    age = age_on(user.birth_date, today) if user.birth_date else None
    return texts.person_label(name, user.username, age, user.id)


@router.post("/reports", status_code=status.HTTP_204_NO_CONTENT)
async def report_user(
    body: ReportIn, user: OnboardedUser, session: SessionDep, notifier: NotifierDep, background: BackgroundTasks
) -> Response:
    """Пожаловаться: человек сразу пропадает у автора (блокировка), жалоба уходит модераторам.
    Повторная жалоба на того же, пока первая не разобрана, модераторов не дёргает."""
    target = await _other_user(session, user, body.user_id)
    match = await _match(session, user.id, target.id)
    in_lobby = body.lobby_id is not None and await _both_in_lobby(session, body.lobby_id, user.id, target.id)
    if match is None and not in_lobby:
        raise _error("user_not_found", status.HTTP_404_NOT_FOUND)

    now = utcnow()
    recent = await session.scalar(
        select(func.count(Report.id)).where(Report.reporter_id == user.id, Report.created_at > now - REPORTS_WINDOW)
    )
    if recent >= REPORTS_PER_DAY:
        raise _error("too_many_reports", status.HTTP_429_TOO_MANY_REQUESTS)

    await _block(session, user, target.id)
    already = await session.scalar(
        select(Report.id).where(
            Report.reporter_id == user.id, Report.target_user_id == target.id, Report.status.in_(OPEN_STATUSES)
        )
    )
    if already is not None:
        await session.commit()
        return _done()

    report = Report(
        reporter_id=user.id,
        target_user_id=target.id,
        lobby_id=body.lobby_id if in_lobby else None,
        reason=body.reason,
        comment=body.comment or None,
        created_at=now,
    )
    session.add(report)
    await session.flush()

    my_profile = await session.get(Profile, user.id)
    names = {
        user.id: my_profile.display_name if my_profile else user.first_name,
        target.id: target.profile.display_name if target.profile else target.first_name,
    }
    card = texts.report_card(
        report.id,
        body.reason.value,
        target=_label(target, target.profile, now.date()),
        reporter=_label(user, my_profile, now.date()),
        comment=report.comment,
        messages=await _context(session, match if not in_lobby else None, body, names),
    )
    moderators = await moderator_telegram_ids(session, notifier.admin_ids)
    await session.commit()

    keyboard = moderation_keyboard(report.id)
    background.add_task(notifier.send, [Note(telegram_id, card, markup=keyboard) for telegram_id in moderators])
    return _done()
