"""Лента людей: анкеты своей возрастной группы, «нравится» / «дальше», мэтчи.

Контакты (ник в Telegram, Discord) открываются только после взаимного лайка.
"""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import OnboardedUser, PhotoUrl, SessionDep
from app.api.schemas import LanguageCode, MatchOut, PersonGameOut, PersonOut, PhotoOut, ReactIn, ReactOut
from app.db.enums import MatchSource, PlayStyle, ReactionKind
from app.db.models import Game, GameRank, Match, Profile, Reaction, User, UserGame
from app.domain.age import age_on
from app.domain.people import CANDIDATE_POOL, SKIP_COOLDOWN, Compatibility, Traits, compatibility
from app.domain.time import utcnow
from app.services.users import ban_inactive_clause, blocked_user_ids

router = APIRouter(tags=["люди"])

PERSON_OPTIONS = (
    selectinload(User.profile),
    selectinload(User.photos),
    selectinload(User.games).selectinload(UserGame.roles),
)


def _visible_people(viewer: User, now) -> list[ColumnElement[bool]]:
    """Кого можно видеть в ленте и лайкать: своя возрастная группа, анкета открыта, нет бана и блокировок."""
    return [
        User.id != viewer.id,
        User.onboarded_at.is_not(None),
        User.age_group == viewer.age_group,
        Profile.is_visible.is_(True),
        ban_inactive_clause(now),
        User.id.not_in(blocked_user_ids(viewer.id)),
    ]


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
    )


def _age(user: User, today: date) -> int | None:
    return age_on(user.birth_date, today) if user.birth_date else None


def _photos(user: User, photo_url: Callable[[int], str]) -> list[PhotoOut]:
    return [PhotoOut(id=photo.id, url=photo_url(photo.id)) for photo in user.photos]


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
        username=other.username,
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
    """Анкеты, отсортированные по «совпадению». Лайкнутые не показываются, пропущенные — вернутся через 3 дня."""
    now = utcnow()
    liked = select(Reaction.to_user_id).where(Reaction.from_user_id == user.id, Reaction.kind == ReactionKind.LIKE)
    skipped = select(Reaction.to_user_id).where(
        Reaction.from_user_id == user.id,
        Reaction.kind == ReactionKind.SKIP,
        Reaction.created_at > now - SKIP_COOLDOWN,
    )
    query = (
        select(User)
        .join(Profile, Profile.user_id == User.id)
        .where(*_visible_people(user, now), User.id.not_in(liked), User.id.not_in(skipped))
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
    person_id: int, body: ReactIn, user: OnboardedUser, session: SessionDep, photo_url: PhotoUrl
) -> ReactOut:
    """«Нравится» или «дальше». Взаимное «нравится» — мэтч, и в ответе сразу контакты."""
    now = utcnow()
    person = await session.scalar(
        select(User)
        .join(Profile, Profile.user_id == User.id)
        .where(User.id == person_id, *_visible_people(user, now))
        .options(*PERSON_OPTIONS)
    )
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="person_not_found")

    reaction = await session.scalar(
        select(Reaction).where(Reaction.from_user_id == user.id, Reaction.to_user_id == person_id)
    )
    if reaction is None:
        session.add(Reaction(from_user_id=user.id, to_user_id=person_id, kind=body.kind, created_at=now))
    else:
        reaction.kind = body.kind
        reaction.created_at = now  # от этого времени считается, когда пропущенный вернётся в ленту

    match = None
    if body.kind == ReactionKind.LIKE:
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
