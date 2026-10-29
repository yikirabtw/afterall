"""Пати («Ищу пати»): создание, лента, отклики и решения создателя.

Кто что видит — в app/api/lobby_views.py, правила и лимиты — в app/domain/lobbies.py.
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.api.deps import NotifierDep, OnboardedUser, SessionDep
from app.api.lobby_views import DETAIL_OPTIONS, FEED_OPTIONS, lobby_detail_out, lobby_out
from app.api.schemas import ApplyIn, LanguageCode, LobbyDetailOut, LobbyFeedOut, LobbyIn, LobbyOut
from app.db.enums import LobbyKind, LobbyStatus, MemberStatus, PlayStyle
from app.db.models import Block, Game, GameRank, Lobby, LobbyMember, Profile, User, UserGame
from app.domain.lobbies import (
    ACTIVE_STATUSES,
    LOBBY_TTL,
    MAX_PENDING_APPLICATIONS,
    MAX_START_AHEAD,
    START_GRACE,
    effective_status,
    rank_fits,
)
from app.bot import texts
from app.domain.plans import ACTIVE_LOBBY_LIMITS
from app.domain.time import utcnow
from app.services.notify import Note
from app.services.plans import plan_of
from app.services.users import ban_inactive_clause, blocked_user_ids, is_ban_active

router = APIRouter(prefix="/lobbies", tags=["пати"])


def _error(code: str, http_status: int = status.HTTP_409_CONFLICT) -> HTTPException:
    return HTTPException(http_status, detail=code)


def _invalid(code: str) -> HTTPException:
    return _error(code, status.HTTP_422_UNPROCESSABLE_CONTENT)


def _not_found() -> HTTPException:
    # Чужую невидимую пати не отличаем от несуществующей — чтобы не выдавать, что она есть
    return _error("lobby_not_found", status.HTTP_404_NOT_FOUND)


async def _is_blocked(session: AsyncSession, a: int, b: int) -> bool:
    count = await session.scalar(
        select(func.count())
        .select_from(Block)
        .where(
            or_(
                and_(Block.blocker_id == a, Block.blocked_id == b),
                and_(Block.blocker_id == b, Block.blocked_id == a),
            )
        )
    )
    return bool(count)


async def _get_visible_lobby(
    session: AsyncSession, lobby_id: int, viewer: User, now: datetime, *, lock: bool = False
) -> Lobby:
    if lock:
        # В Postgres блокируем строку, чтобы два одновременных «принять» не переполнили пати
        await session.execute(select(Lobby.id).where(Lobby.id == lobby_id).with_for_update())
    lobby = await session.scalar(
        select(Lobby)
        .where(Lobby.id == lobby_id)
        .options(*DETAIL_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if lobby is None:
        raise _not_found()
    if any(member.user_id == viewer.id for member in lobby.members):
        return lobby  # участники и откликнувшиеся видят пати всегда
    if (
        lobby.age_group != viewer.age_group
        or is_ban_active(lobby.owner, now)
        or await _is_blocked(session, viewer.id, lobby.owner_id)
    ):
        raise _not_found()
    return lobby


async def _get_owned_lobby(
    session: AsyncSession, lobby_id: int, owner: User, now: datetime, *, lock: bool = False
) -> Lobby:
    lobby = await _get_visible_lobby(session, lobby_id, owner, now, lock=lock)
    if lobby.owner_id != owner.id:
        raise _error("not_lobby_owner", status.HTTP_403_FORBIDDEN)
    return lobby


def _membership(lobby: Lobby, user_id: int) -> LobbyMember | None:
    return next((member for member in lobby.members if member.user_id == user_id), None)


def _accepted_count(lobby: Lobby) -> int:
    return sum(member.status == MemberStatus.ACCEPTED for member in lobby.members)


def _reopen_if_full(lobby: Lobby, now: datetime) -> None:
    if lobby.status == LobbyStatus.FULL and effective_status(lobby.status, lobby.expires_at, now) == LobbyStatus.FULL:
        lobby.status = LobbyStatus.OPEN


async def _rank_tier(session: AsyncSession, rank_id: int | None) -> int | None:
    if rank_id is None:
        return None
    return await session.scalar(select(GameRank.tier).where(GameRank.id == rank_id))


async def _my_rank_tier(session: AsyncSession, user_id: int, game_id: int | None) -> int | None:
    return await session.scalar(
        select(GameRank.tier)
        .join(UserGame, UserGame.rank_id == GameRank.id)
        .where(UserGame.user_id == user_id, UserGame.game_id == game_id)
    )


async def _detail(session: AsyncSession, lobby_id: int, viewer: User, now: datetime) -> LobbyDetailOut:
    return lobby_detail_out(await _get_visible_lobby(session, lobby_id, viewer, now), viewer.id, now)


# --- Создание ---


@router.post("", response_model=LobbyDetailOut, status_code=status.HTTP_201_CREATED)
async def create_lobby(body: LobbyIn, user: OnboardedUser, session: SessionDep) -> LobbyDetailOut:
    """Создать заявку «Ищу пати». Пати видна только возрастной группе создателя и живёт 3 часа от начала."""
    now = utcnow()
    active_owned = await session.scalar(
        select(func.count(Lobby.id)).where(
            Lobby.owner_id == user.id, Lobby.status.in_(ACTIVE_STATUSES), Lobby.expires_at > now
        )
    )
    # Сколько своих пати может быть открыто сразу — по тарифу (бесплатно 2, Plus 5, Premium 10)
    plan, _ = await plan_of(session, user.id, now)
    if active_owned >= ACTIVE_LOBBY_LIMITS[plan]:
        raise _error("too_many_active_lobbies" if plan == "premium" else "lobbies_need_plan")
    if body.starts_at is not None and not (now - START_GRACE <= body.starts_at <= now + MAX_START_AHEAD):
        raise _invalid("starts_at_out_of_range")

    if body.kind == LobbyKind.GAME:
        game = await session.scalar(
            select(Game).where(Game.id == body.game_id, Game.is_active).options(selectinload(Game.ranks))
        )
        if game is None:
            raise _invalid("unknown_game")
        if game.max_party_size and body.slots_total > game.max_party_size:
            raise _invalid("party_too_big")
        ranks = {rank.id: rank for rank in game.ranks}
        for rank_id in (body.rank_min_id, body.rank_max_id):
            if rank_id is not None and rank_id not in ranks:
                raise _invalid("rank_not_in_game")
        if body.rank_min_id and body.rank_max_id and ranks[body.rank_min_id].tier > ranks[body.rank_max_id].tier:
            raise _invalid("invalid_rank_range")

    lobby = Lobby(
        **body.model_dump(),
        owner_id=user.id,
        age_group=user.age_group,
        status=LobbyStatus.OPEN,
        expires_at=(body.starts_at or now) + LOBBY_TTL,
    )
    lobby.members = [LobbyMember(user_id=user.id, is_owner=True, status=MemberStatus.ACCEPTED, decided_at=now)]
    session.add(lobby)
    await session.commit()
    return await _detail(session, lobby.id, user, now)


# --- Лента и просмотр ---


def _only_fitting(query: Select, user: User, has_mic: bool) -> Select:
    """Оставляет только пати, куда пользователь может откликнуться: по микрофону и рангу."""
    if not has_mic:
        query = query.where(Lobby.need_mic.is_(False))
    my_tier = (
        select(GameRank.tier)
        .join(UserGame, UserGame.rank_id == GameRank.id)
        .where(UserGame.user_id == user.id, UserGame.game_id == Lobby.game_id)
        .correlate(Lobby)
        .scalar_subquery()
    )
    min_rank, max_rank = aliased(GameRank), aliased(GameRank)
    return (
        query.outerjoin(min_rank, Lobby.rank_min_id == min_rank.id)
        .outerjoin(max_rank, Lobby.rank_max_id == max_rank.id)
        .where(
            # Если ранга у пользователя нет, а требования есть — сравнение даёт NULL и пати отсеивается
            or_(Lobby.rank_min_id.is_(None), my_tier >= min_rank.tier),
            or_(Lobby.rank_max_id.is_(None), my_tier <= max_rank.tier),
        )
    )


@router.get("", response_model=LobbyFeedOut)
async def lobby_feed(
    user: OnboardedUser,
    session: SessionDep,
    game_id: int | None = None,
    kind: LobbyKind | None = None,
    language: LanguageCode | None = None,
    play_style: Annotated[PlayStyle | None, Query(description="Пати без требования к стилю тоже попадают")] = None,
    fits_me: Annotated[bool, Query(description="Только те, куда подхожу по микрофону и рангу")] = False,
    cursor: Annotated[int | None, Query(description="next_cursor из предыдущей страницы")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> LobbyFeedOut:
    """Лента открытых пати своей возрастной группы, новые сверху. Свои пати сюда не попадают — они в /mine."""
    now = utcnow()
    query = (
        select(Lobby)
        .join(User, Lobby.owner_id == User.id)
        .where(
            Lobby.status == LobbyStatus.OPEN,
            Lobby.expires_at > now,
            Lobby.age_group == user.age_group,
            Lobby.owner_id != user.id,
            Lobby.owner_id.not_in(blocked_user_ids(user.id)),
            ban_inactive_clause(now),
        )
        .options(*FEED_OPTIONS)
        .order_by(Lobby.id.desc())
        .limit(limit + 1)
    )
    if game_id is not None:
        query = query.where(Lobby.game_id == game_id)
    if kind is not None:
        query = query.where(Lobby.kind == kind)
    if language is not None:
        query = query.where(Lobby.language == language)
    if play_style is not None:
        query = query.where(or_(Lobby.play_style == play_style, Lobby.play_style.is_(None)))
    if cursor is not None:
        query = query.where(Lobby.id < cursor)
    if fits_me:
        profile = await session.get(Profile, user.id)
        query = _only_fitting(query, user, has_mic=bool(profile and profile.has_mic))

    lobbies = list(await session.scalars(query))
    has_more = len(lobbies) > limit
    lobbies = lobbies[:limit]
    return LobbyFeedOut(
        items=[lobby_out(lobby, user.id, now) for lobby in lobbies],
        next_cursor=lobbies[-1].id if has_more else None,
    )


@router.get("/mine", response_model=list[LobbyOut])
async def my_lobbies(user: OnboardedUser, session: SessionDep) -> list[LobbyOut]:
    """Мои пати: созданные, где меня приняли и куда я откликнулся. Закончившиеся показываются ещё сутки."""
    now = utcnow()
    my_lobby_ids = select(LobbyMember.lobby_id).where(
        LobbyMember.user_id == user.id,
        LobbyMember.status.in_([MemberStatus.PENDING, MemberStatus.ACCEPTED]),
    )
    lobbies = await session.scalars(
        select(Lobby)
        .where(
            Lobby.id.in_(my_lobby_ids),
            Lobby.status != LobbyStatus.CANCELLED,
            Lobby.expires_at > now - timedelta(hours=24),
        )
        .options(*FEED_OPTIONS)
        .order_by(Lobby.expires_at.desc())
    )
    return [lobby_out(lobby, user.id, now) for lobby in lobbies]


@router.get("/{lobby_id}", response_model=LobbyDetailOut)
async def get_lobby(lobby_id: int, user: OnboardedUser, session: SessionDep) -> LobbyDetailOut:
    """Карточка пати. Создатель видит откликнувшихся, принятые — друг друга и контакты."""
    return await _detail(session, lobby_id, user, utcnow())


# --- Отклики ---


async def _telegram_id(session: AsyncSession, user_id: int) -> int:
    return await session.scalar(select(User.telegram_id).where(User.id == user_id))


@router.post("/{lobby_id}/apply", response_model=LobbyDetailOut)
async def apply_to_lobby(
    lobby_id: int,
    user: OnboardedUser,
    session: SessionDep,
    notifier: NotifierDep,
    background: BackgroundTasks,
    body: ApplyIn | None = None,
) -> LobbyDetailOut:
    """Откликнуться на пати (сообщение создателю — по желанию). Проверяет микрофон и ранг, если пати их требует.

    Создателю приходит уведомление в боте с кнопкой, открывающей пати.
    """
    now = utcnow()
    note = body.note if body else None
    lobby = await _get_visible_lobby(session, lobby_id, user, now)
    if lobby.owner_id == user.id:
        raise _error("cannot_apply_own_lobby")
    current_status = effective_status(lobby.status, lobby.expires_at, now)
    if current_status == LobbyStatus.FULL:
        raise _error("lobby_full")
    if current_status != LobbyStatus.OPEN:
        raise _error("lobby_not_active")

    membership = _membership(lobby, user.id)
    if membership is not None:
        if membership.status in (MemberStatus.PENDING, MemberStatus.ACCEPTED):
            raise _error("already_applied")
        if membership.status == MemberStatus.DECLINED:
            raise _error("application_declined")
        if membership.status == MemberStatus.KICKED:
            raise _error("kicked_from_lobby")
        # LEFT — сам вышел раньше, можно откликнуться снова

    pending = await session.scalar(
        select(func.count(LobbyMember.id))
        .join(Lobby, LobbyMember.lobby_id == Lobby.id)
        .where(
            LobbyMember.user_id == user.id,
            LobbyMember.status == MemberStatus.PENDING,
            Lobby.status == LobbyStatus.OPEN,
            Lobby.expires_at > now,
        )
    )
    if pending >= MAX_PENDING_APPLICATIONS:
        raise _error("too_many_applications")

    profile = await session.get(Profile, user.id)
    if lobby.need_mic and not (profile and profile.has_mic):
        raise _invalid("mic_required")
    min_tier = await _rank_tier(session, lobby.rank_min_id)
    max_tier = await _rank_tier(session, lobby.rank_max_id)
    if not rank_fits(await _my_rank_tier(session, user.id, lobby.game_id), min_tier, max_tier):
        raise _invalid("rank_out_of_range")

    if membership is None:
        session.add(LobbyMember(lobby_id=lobby.id, user_id=user.id, status=MemberStatus.PENDING, note=note))
    else:
        membership.status = MemberStatus.PENDING
        membership.note = note
        membership.decided_at = None
    await session.commit()

    name = profile.display_name if profile else user.first_name
    text = texts.notify_application(name, lobby.title, note)
    owner = Note(await _telegram_id(session, lobby.owner_id), text, texts.BUTTON_OPEN_LOBBY, f"lobby/{lobby.id}")
    background.add_task(notifier.send, [owner])
    return await _detail(session, lobby.id, user, now)


@router.post("/{lobby_id}/leave", response_model=LobbyDetailOut)
async def leave_lobby(lobby_id: int, user: OnboardedUser, session: SessionDep) -> LobbyDetailOut:
    """Отозвать отклик или выйти из пати. Место освобождается, заполненная пати снова открывается."""
    now = utcnow()
    lobby = await _get_visible_lobby(session, lobby_id, user, now)
    membership = _membership(lobby, user.id)
    if membership is None or membership.status not in (MemberStatus.PENDING, MemberStatus.ACCEPTED):
        raise _error("not_a_member")
    if membership.is_owner:
        raise _error("owner_cannot_leave")

    was_accepted = membership.status == MemberStatus.ACCEPTED
    membership.status = MemberStatus.LEFT
    membership.decided_at = now
    if was_accepted:
        _reopen_if_full(lobby, now)
    await session.commit()
    return await _detail(session, lobby.id, user, now)


# --- Решения создателя ---


def _find_member(lobby: Lobby, member_id: int) -> LobbyMember:
    member = _membership(lobby, member_id)
    if member is None or member.is_owner:
        raise _error("member_not_found", status.HTTP_404_NOT_FOUND)
    return member


@router.post("/{lobby_id}/members/{member_id}/accept", response_model=LobbyDetailOut)
async def accept_member(
    lobby_id: int,
    member_id: int,
    user: OnboardedUser,
    session: SessionDep,
    notifier: NotifierDep,
    background: BackgroundTasks,
) -> LobbyDetailOut:
    """Принять откликнувшегося (member_id — его user_id). Когда места кончаются, пати становится full."""
    now = utcnow()
    lobby = await _get_owned_lobby(session, lobby_id, user, now, lock=True)
    current_status = effective_status(lobby.status, lobby.expires_at, now)
    if current_status == LobbyStatus.FULL:
        raise _error("lobby_full")
    if current_status != LobbyStatus.OPEN:
        raise _error("lobby_not_active")
    member = _find_member(lobby, member_id)
    if member.status != MemberStatus.PENDING:
        raise _error("member_not_pending")

    member.status = MemberStatus.ACCEPTED
    member.decided_at = now
    if _accepted_count(lobby) >= lobby.slots_total:
        lobby.status = LobbyStatus.FULL
    await session.commit()

    text = texts.notify_accepted(lobby.title)
    note = Note(await _telegram_id(session, member_id), text, texts.BUTTON_PARTY_CHAT, f"chat/lobby/{lobby.id}")
    background.add_task(notifier.send, [note])
    return await _detail(session, lobby.id, user, now)


@router.post("/{lobby_id}/members/{member_id}/decline", response_model=LobbyDetailOut)
async def decline_member(
    lobby_id: int,
    member_id: int,
    user: OnboardedUser,
    session: SessionDep,
    notifier: NotifierDep,
    background: BackgroundTasks,
) -> LobbyDetailOut:
    """Отклонить отклик. Повторно откликнуться в эту пати человек уже не сможет."""
    now = utcnow()
    lobby = await _get_owned_lobby(session, lobby_id, user, now)
    member = _find_member(lobby, member_id)
    if member.status != MemberStatus.PENDING:
        raise _error("member_not_pending")

    member.status = MemberStatus.DECLINED
    member.decided_at = now
    await session.commit()

    note = Note(await _telegram_id(session, member_id), texts.notify_declined(lobby.title), texts.BUTTON_FEED, "feed")
    background.add_task(notifier.send, [note])
    return await _detail(session, lobby.id, user, now)


@router.post("/{lobby_id}/members/{member_id}/kick", response_model=LobbyDetailOut)
async def kick_member(lobby_id: int, member_id: int, user: OnboardedUser, session: SessionDep) -> LobbyDetailOut:
    """Убрать принятого участника. Вернуться в эту пати он не сможет."""
    now = utcnow()
    lobby = await _get_owned_lobby(session, lobby_id, user, now)
    member = _find_member(lobby, member_id)
    if member.status != MemberStatus.ACCEPTED:
        raise _error("member_not_accepted")

    member.status = MemberStatus.KICKED
    member.decided_at = now
    _reopen_if_full(lobby, now)
    await session.commit()
    return await _detail(session, lobby.id, user, now)


@router.post("/{lobby_id}/cancel", response_model=LobbyDetailOut)
async def cancel_lobby(lobby_id: int, user: OnboardedUser, session: SessionDep) -> LobbyDetailOut:
    """Отменить пати. Она пропадает из ленты и из «моих пати»."""
    now = utcnow()
    lobby = await _get_owned_lobby(session, lobby_id, user, now)
    if lobby.status in ACTIVE_STATUSES:
        lobby.status = LobbyStatus.CANCELLED
        await session.commit()
    return await _detail(session, lobby.id, user, now)
