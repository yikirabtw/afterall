"""Лента людей: анкеты по взаимному возрасту поиска (рамки — domain/age.py), «нравится» / «дальше», мэтчи.

После взаимного лайка открываются чат в приложении и Discord; ник в Telegram — только если человек разрешил.
"""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response, status
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import NotifierDep, OnboardedUser, PhotoUrl, SessionDep
from app.api.schemas import LanguageCode, MatchOut, PersonGameOut, PersonOut, PhotoOut, ReactIn, ReactOut
from app.db.enums import MatchSource, PlayStyle, ReactionKind
from app.db.models import Game, GameRank, Match, Profile, Reaction, User, UserGame
from app.domain.age import age_on, search_range, search_range_fits, years_ago
from app.domain.people import CANDIDATE_POOL, SKIP_COOLDOWN, Compatibility, Traits, compatibility
from app.domain.time import utcnow
from app.bot import texts
from app.services.notify import Note
from app.services.users import ban_inactive_clause, blocked_user_ids

router = APIRouter(tags=["люди"])

PERSON_OPTIONS = (
    selectinload(User.profile),
    selectinload(User.photos),
    selectinload(User.games).selectinload(UserGame.roles),
)


def _visible_people(viewer: User, profile: Profile, now) -> list[ColumnElement[bool]]:
    """Кого можно видеть в ленте и лайкать: анкета открыта, нет бана и блокировок, возраст подходит обоим.

    Возраст: человек попадает в мой диапазон (уже обрезанный рамками), а я — в его выбор.
    Рамки симметричные (domain/age.search_limits), поэтому проверять их со второй стороны не нужно.
    """
    today = now.date()
    my_age = age_on(viewer.birth_date, today)
    start, end = search_range(my_age, profile.search_age_min, profile.search_age_max)
    conditions = [
        User.id != viewer.id,
        User.onboarded_at.is_not(None),
        User.birth_date <= years_ago(today, start),
        or_(Profile.search_age_min.is_(None), Profile.search_age_min <= my_age),
        or_(Profile.search_age_max.is_(None), Profile.search_age_max >= my_age),
        Profile.is_visible.is_(True),
        ban_inactive_clause(now),
        User.id.not_in(blocked_user_ids(viewer.id)),
    ]
    if end is not None:
        conditions.append(User.birth_date > years_ago(today, end + 1))
    return conditions


async def _my_profile(session: AsyncSession, user: User, now) -> Profile:
    """Своя анкета для подбора. Выбор возраста, целиком выпавший из рамок после дня рождения, сбрасывается —
    иначе человека не увидел бы никто: другие проверяют свой возраст по его устаревшему выбору."""
    profile = await session.get(Profile, user.id)
    if not search_range_fits(age_on(user.birth_date, now.date()), profile.search_age_min, profile.search_age_max):
        profile.search_age_min = profile.search_age_max = None
        await session.commit()
    return profile


async def _load_person(session: AsyncSession, user_id: int) -> User:
    return await session.scalar(select(User).where(User.id == user_id).options(*PERSON_OPTIONS))


async def _reference(session: AsyncSession) -> tuple[dict[int, int], dict[int, str]]:
    """Справочники для совпадения: ранг → tier и игра → название."""
    tiers = dict((await session.execute(select(GameRank.id, GameRank.tier))).all())
    names = dict((await session.execute(select(Game.id, Game.name))).all())
    return tiers, names


def _traits(user: User, tiers: dict[int, int]) -> Traits:
    profile = user.profile
    return Traits(
        games={game.game_id: tiers.get(game.rank_id) if game.rank_id else None for game in user.games},
        main_game_id=next((game.game_id for game in user.games if game.is_main), None),
        play_style=profile.play_style,
        looking_for=profile.looking_for,
        languages=set(profile.languages),
        has_mic=profile.has_mic,
        faceit={game.game_id: game.faceit_elo for game in user.games if game.faceit_elo is not None},
    )


def _age(user: User, today: date) -> int | None:
    return age_on(user.birth_date, today) if user.birth_date else None


def _photos(user: User, photo_url: Callable[[int], str]) -> list[PhotoOut]:
    return [PhotoOut(id=photo.id, url=photo_url(photo.id), width=photo.width, height=photo.height) for photo in user.photos]


def _person_out(user: User, match: Compatibility, photo_url: Callable[[int], str], today: date) -> PersonOut:
    profile = user.profile
    return PersonOut(
        user_id=user.id,
        display_name=profile.display_name,
        age=_age(user, today),
        city=profile.city,
        bio=profile.bio,
        has_mic=profile.has_mic,
        play_style=profile.play_style,
        looking_for=profile.looking_for,
        languages=profile.languages,
        reputation=profile.reputation,
        photos=_photos(user, photo_url),
        games=[PersonGameOut.model_validate(game) for game in user.games],
        compatibility=match.score,
        common_game_ids=match.common_game_ids,
        reasons=match.reasons,
    )


def _match_out(other: User, match: Match, photo_url: Callable[[int], str], today: date) -> MatchOut:
    profile = other.profile
    return MatchOut(
        user_id=other.id,
        display_name=profile.display_name,
        age=_age(other, today),
        photos=_photos(other, photo_url),
        main_game_id=next((game.game_id for game in other.games if game.is_main), None),
        username=other.username if profile.show_telegram else None,
        discord_tag=profile.discord_tag,
        matched_at=match.created_at,
    )


@router.get("/people", response_model=list[PersonOut])
async def people_feed(
    user: OnboardedUser,
    session: SessionDep,
    photo_url: PhotoUrl,
    game_id: int | None = None,
    need_mic: Annotated[bool, Query(description="Только с микрофоном")] = False,
    play_style: PlayStyle | None = None,
    language: LanguageCode | None = None,
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> list[PersonOut]:
    """Анкеты, отсортированные по «совпадению». Лайкнутые и удалённые из мэтчей не показываются,
    пропущенные — вернутся через 3 дня."""
    now = utcnow()
    liked = select(Reaction.to_user_id).where(
        Reaction.from_user_id == user.id, Reaction.kind.in_((ReactionKind.LIKE, ReactionKind.UNMATCH))
    )
    skipped = select(Reaction.to_user_id).where(
        Reaction.from_user_id == user.id,
        Reaction.kind == ReactionKind.SKIP,
        Reaction.created_at > now - SKIP_COOLDOWN,
    )
    profile = await _my_profile(session, user, now)
    query = (
        select(User)
        .join(Profile, Profile.user_id == User.id)
        .where(*_visible_people(user, profile, now), User.id.not_in(liked), User.id.not_in(skipped))
        .options(*PERSON_OPTIONS)
        .order_by(User.last_seen_at.desc().nulls_last())
        .limit(CANDIDATE_POOL)
    )
    if game_id is not None:
        query = query.where(User.id.in_(select(UserGame.user_id).where(UserGame.game_id == game_id)))
    if need_mic:
        query = query.where(Profile.has_mic.is_(True))
    if play_style is not None:
        query = query.where(Profile.play_style == play_style)

    candidates = list(await session.scalars(query))
    if language is not None:
        # Языки лежат JSON-списком — фильтр одинаково работает и в SQLite, и в Postgres, только в Python
        candidates = [person for person in candidates if language in person.profile.languages]

    tiers, names = await _reference(session)
    me = _traits(await _load_person(session, user.id), tiers)
    scored = [(compatibility(me, _traits(person, tiers), names), person) for person in candidates]
    # Сортировка устойчивая: при равном совпадении первыми остаются недавно заходившие
    scored.sort(key=lambda pair: pair[0].score, reverse=True)
    today = now.date()
    return [_person_out(person, match, photo_url, today) for match, person in scored[:limit]]


@router.post("/people/{person_id}/react", response_model=ReactOut)
async def react_to_person(
    person_id: int,
    body: ReactIn,
    user: OnboardedUser,
    session: SessionDep,
    photo_url: PhotoUrl,
    notifier: NotifierDep,
    background: BackgroundTasks,
) -> ReactOut:
    """«Нравится» или «дальше». Взаимное «нравится» — мэтч, и в ответе сразу контакты.

    Кто лайкнул вторым, узнаёт о мэтче сразу в приложении, а первому приходит уведомление в боте.
    """
    now = utcnow()
    kind = ReactionKind(body.kind)
    profile = await _my_profile(session, user, now)
    person = await session.scalar(
        select(User)
        .join(Profile, Profile.user_id == User.id)
        .where(User.id == person_id, *_visible_people(user, profile, now))
        .options(*PERSON_OPTIONS)
    )
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="person_not_found")

    reaction = await session.scalar(
        select(Reaction).where(Reaction.from_user_id == user.id, Reaction.to_user_id == person_id)
    )
    if reaction is None:
        session.add(Reaction(from_user_id=user.id, to_user_id=person_id, kind=kind, created_at=now))
    else:
        reaction.kind = kind
        reaction.created_at = now  # от этого времени считается, когда пропущенный вернётся в ленту

    match = None
    if kind == ReactionKind.LIKE:
        mutual = await session.scalar(
            select(Reaction.id).where(
                Reaction.from_user_id == person_id,
                Reaction.to_user_id == user.id,
                Reaction.kind == ReactionKind.LIKE,
            )
        )
        if mutual:
            user_a_id, user_b_id = sorted((user.id, person_id))
            match = await session.scalar(select(Match).where(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id))
            if match is None:
                match = Match(user_a_id=user_a_id, user_b_id=user_b_id, source=MatchSource.FEED, created_at=now)
                session.add(match)
                note = Note(
                    person.telegram_id, texts.notify_match(profile.display_name), texts.BUTTON_WRITE, f"chat/direct/{user.id}"
                )
                background.add_task(notifier.send, [note])
    await session.commit()
    return ReactOut(match=_match_out(person, match, photo_url, now.date()) if match else None)


@router.get("/matches", response_model=list[MatchOut])
async def my_matches(user: OnboardedUser, session: SessionDep, photo_url: PhotoUrl) -> list[MatchOut]:
    """Взаимные лайки, новые сверху. Заблокированные в любую сторону не показываются."""
    matches = list(
        await session.scalars(
            select(Match)
            .where(or_(Match.user_a_id == user.id, Match.user_b_id == user.id))
            .order_by(Match.created_at.desc(), Match.id.desc())
        )
    )
    other_ids = {match.user_b_id if match.user_a_id == user.id else match.user_a_id for match in matches}
    blocked = set(await session.scalars(blocked_user_ids(user.id)))
    people = {
        person.id: person
        for person in await session.scalars(
            select(User).where(User.id.in_(other_ids - blocked)).options(*PERSON_OPTIONS)
        )
    }
    today = utcnow().date()
    result = []
    for match in matches:
        other_id = match.user_b_id if match.user_a_id == user.id else match.user_a_id
        if other_id in people:
            result.append(_match_out(people[other_id], match, photo_url, today))
    return result


@router.delete("/matches/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(person_id: int, user: OnboardedUser, session: SessionDep) -> Response:
    """Удалить мэтч у обоих. Личный чат уходит вместе с ним (каскад в базе).

    Своя реакция становится «unmatch»: человек не вернётся в ленту, а его повторный лайк не создаст мэтч заново.
    """
    user_a_id, user_b_id = sorted((user.id, person_id))
    match = await session.scalar(select(Match).where(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id))
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="match_not_found")
    await session.delete(match)

    now = utcnow()
    reaction = await session.scalar(
        select(Reaction).where(Reaction.from_user_id == user.id, Reaction.to_user_id == person_id)
    )
    if reaction is None:  # мэтч мог появиться не из ленты
        session.add(Reaction(from_user_id=user.id, to_user_id=person_id, kind=ReactionKind.UNMATCH, created_at=now))
    else:
        reaction.kind = ReactionKind.UNMATCH
        reaction.created_at = now
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
