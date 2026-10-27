from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import AgeGroup, LobbyKind, MemberStatus, ReactionKind
from app.db.models import Game, GameRank, Lobby, LobbyMember, Match, Profile, Reaction, User, UserGame
from app.domain.age import age_group_for


def make_user(session, telegram_id: int, age_group=AgeGroup.TEEN_16_17) -> User:
    user = User(telegram_id=telegram_id, first_name=f"user{telegram_id}", age_group=age_group)
    user.profile = Profile(display_name=f"user{telegram_id}")
    session.add(user)
    session.flush()
    return user


def make_game(session) -> Game:
    game = Game(slug="dota2", name="Dota 2", platforms=["pc"], max_party_size=5)
    game.ranks = [GameRank(code="herald", name="Рекрут", tier=1), GameRank(code="guardian", name="Страж", tier=2)]
    session.add(game)
    session.flush()
    return game


def test_user_with_profile_and_game(session):
    game = make_game(session)
    user = make_user(session, 1)
    user.games.append(UserGame(game=game, rank=game.ranks[1], is_main=True))
    session.commit()

    assert user.profile.languages == ["ru"]
    assert user.games[0].rank.name == "Страж"


def test_telegram_id_is_unique(session):
    make_user(session, 1)
    with pytest.raises(IntegrityError):
        make_user(session, 1)


def test_lobby_with_application(session):
    game = make_game(session)
    owner, guest = make_user(session, 1), make_user(session, 2)
    lobby = Lobby(
        owner=owner,
        kind=LobbyKind.GAME,
        game=game,
        title="Нужны 2 в пати",
        slots_total=5,
        age_group=owner.age_group,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )
    lobby.members = [LobbyMember(user=owner, is_owner=True, status=MemberStatus.ACCEPTED), LobbyMember(user=guest)]
    session.add(lobby)
    session.commit()

    assert [m.status for m in lobby.members] == [MemberStatus.ACCEPTED, MemberStatus.PENDING]

    # Повторный отклик того же человека запрещён
    session.add(LobbyMember(lobby=lobby, user=guest))
    with pytest.raises(IntegrityError):
        session.flush()


def test_game_lobby_requires_game(session):
    owner = make_user(session, 1)
    session.add(
        Lobby(
            owner=owner,
            kind=LobbyKind.GAME,
            title="Без игры",
            slots_total=3,
            age_group=owner.age_group,
            expires_at=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cannot_react_to_self(session):
    user = make_user(session, 1)
    session.add(Reaction(from_user_id=user.id, to_user_id=user.id, kind=ReactionKind.LIKE))
    with pytest.raises(IntegrityError):
        session.flush()


def test_match_pair_is_ordered(session):
    a, b = make_user(session, 1), make_user(session, 2)
    session.add(Match(user_a_id=b.id, user_b_id=a.id, source="feed"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_user_removes_their_data(session):
    game = make_game(session)
    user = make_user(session, 1)
    user.games.append(UserGame(game=game))
    session.commit()

    session.delete(user)
    session.commit()

    assert session.query(Profile).count() == 0
    assert session.query(UserGame).count() == 0


@pytest.mark.parametrize(
    ("birth_date", "expected"),
    [
        (date(2014, 6, 1), None),  # 12 лет
        (date(2013, 3, 1), AgeGroup.TEEN_13_15),  # 13 исполнилось
        (date(2010, 6, 2), AgeGroup.TEEN_13_15),  # 16 исполнится завтра
        (date(2010, 6, 1), AgeGroup.TEEN_16_17),  # 16 сегодня
        (date(2008, 6, 2), AgeGroup.TEEN_16_17),  # 18 исполнится завтра
        (date(2008, 6, 1), AgeGroup.ADULT),  # 18 сегодня
    ],
)
def test_age_group(birth_date, expected):
    assert age_group_for(birth_date, today=date(2026, 6, 1)) == expected
