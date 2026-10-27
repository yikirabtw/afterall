"""Лента людей: кого видно, «Совпадение N%», лайки, пропуски и мэтчи с контактами."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.db.enums import AgeGroup, LookingFor, PlayStyle, ReactionKind
from app.db.models import Block, Reaction
from app.domain.people import Traits, compatibility
from app.domain.time import utcnow


async def feed(client, player, **params) -> list[dict]:
    response = await client.get("/api/people", params=params, headers=player.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def react(client, player, target, kind: str = "like") -> dict:
    response = await client.post(f"/api/people/{target.id}/react", json={"kind": kind}, headers=player.headers)
    assert response.status_code == 200, response.text
    return response.json()


# --- Совпадение ---


def traits(**overrides) -> Traits:
    base = dict(
        games={1: 2},
        main_game_id=1,
        play_style=PlayStyle.CHILL,
        looking_for=LookingFor.GAMES,
        languages={"ru"},
        has_mic=True,
    )
    return Traits(**{**base, **overrides})


def test_perfect_match_with_one_game_scores_95_with_reasons():
    result = compatibility(traits(), traits(games={1: 3}), {1: "Dota 2"})

    assert result.score == 95
    assert result.common_game_ids == [1]
    # Не больше трёх причин, самые важные первыми
    assert result.reasons == ["Оба играете в Dota 2", "Близкий ранг в Dota 2", "Один стиль — чилл"]


def test_perfect_match_with_two_games_scores_100():
    names = {1: "Dota 2", 2: "CS2"}
    result = compatibility(traits(games={1: 2, 2: None}), traits(games={1: 2, 2: None}), names)

    assert result.score == 100
    assert result.reasons[0] == "Оба играете в Dota 2 и CS2"


def test_nothing_in_common_scores_low():
    result = compatibility(
        traits(),
        traits(games={2: None}, main_game_id=2, play_style=PlayStyle.TRYHARD, looking_for=LookingFor.HANGOUT,
               languages={"en"}, has_mic=False),
        {1: "Dota 2", 2: "CS2"},
    )
    assert result.score == 0
    assert result.reasons == []


def test_far_rank_gives_no_rank_bonus():
    near = compatibility(traits(games={1: 2}), traits(games={1: 3}), {1: "Dota 2"}).score
    far = compatibility(traits(games={1: 1}), traits(games={1: 3}), {1: "Dota 2"}).score
    assert near - far == 10


# --- Лента ---


async def test_feed_shows_only_own_age_group_and_visible(client, make_player):
    me = await make_player()
    peer = await make_player()
    await make_player(AgeGroup.ADULT)
    await make_player(visible=False)
    await make_player(banned=True)

    people = await feed(client, me)

    assert [person["user_id"] for person in people] == [peer.id]
    assert "username" not in people[0] and "discord_tag" not in people[0]  # контактов в ленте нет


async def test_feed_is_sorted_by_compatibility(client, make_player):
    me = await make_player(games={"dota": "guardian"}, play_style=PlayStyle.CHILL)
    stranger = await make_player(games={"cs2": None}, play_style=PlayStyle.TRYHARD, has_mic=False)
    teammate = await make_player(games={"dota": "crusader"}, play_style=PlayStyle.CHILL)

    people = await feed(client, me)

    assert [person["user_id"] for person in people] == [teammate.id, stranger.id]
    best = people[0]
    assert best["compatibility"] > people[1]["compatibility"]
    assert best["reasons"][0] == "Оба играете в Dota 2"
    assert best["common_game_ids"]


async def test_feed_filters(client, make_player, world):
    me = await make_player()
    cs_player = await make_player(games={"cs2": "p0"})
    silent = await make_player(has_mic=False)
    english = await make_player(languages=["en"])

    assert {p["user_id"] for p in await feed(client, me, game_id=world["cs2"])} == {cs_player.id}
    assert silent.id not in {p["user_id"] for p in await feed(client, me, need_mic=True)}
    assert {p["user_id"] for p in await feed(client, me, language="en")} == {english.id}


@pytest.mark.parametrize("blocked_by_me", [True, False])
async def test_blocks_hide_people_both_ways(client, session_maker, make_player, blocked_by_me):
    me, other = await make_player(), await make_player()
    async with session_maker.begin() as session:
        pair = (me.id, other.id) if blocked_by_me else (other.id, me.id)
        session.add(Block(blocker_id=pair[0], blocked_id=pair[1]))

    assert await feed(client, me) == []
    response = await client.post(f"/api/people/{other.id}/react", json={"kind": "like"}, headers=me.headers)
    assert response.status_code == 404


async def test_liked_disappear_and_skipped_come_back(client, session_maker, make_player):
    me, liked, skipped = await make_player(), await make_player(), await make_player()
    await react(client, me, liked, "like")
    await react(client, me, skipped, "skip")

    assert await feed(client, me) == []

    # Через 3 дня пропущенный снова появится, а лайкнутый — нет
    async with session_maker.begin() as session:
        await session.execute(update(Reaction).values(created_at=utcnow() - timedelta(days=4)))
    assert [p["user_id"] for p in await feed(client, me)] == [skipped.id]


async def test_not_onboarded_cannot_use_feed(client):
    from initdata import auth

    response = await client.get("/api/people", headers=auth())
    assert response.json()["detail"] == "onboarding_required"


# --- Лайки и мэтчи ---


async def test_one_sided_like_is_not_a_match(client, make_player):
    me, other = await make_player(), await make_player()

    assert (await react(client, me, other))["match"] is None
    assert (await client.get("/api/matches", headers=me.headers)).json() == []


async def test_mutual_like_creates_match_with_contacts(client, make_player):
    me, other = await make_player(), await make_player()
    await react(client, other, me, "like")

    result = await react(client, me, other, "like")

    match = result["match"]
    assert (match["user_id"], match["username"], match["discord_tag"]) == (other.id, other.username, f"{other.username}_dc")
    mine = (await client.get("/api/matches", headers=me.headers)).json()
    theirs = (await client.get("/api/matches", headers=other.headers)).json()
    assert [m["user_id"] for m in mine] == [other.id]
    assert [m["user_id"] for m in theirs] == [me.id]


async def test_like_after_skip_counts(client, make_player):
    me, other = await make_player(), await make_player()
    await react(client, me, other, "skip")
    await react(client, other, me, "like")

    assert (await react(client, me, other, "like"))["match"] is not None


async def test_repeated_like_does_not_duplicate_match(client, session_maker, make_player):
    me, other = await make_player(), await make_player()
    await react(client, other, me)
    await react(client, me, other)
    await react(client, me, other)

    assert len((await client.get("/api/matches", headers=me.headers)).json()) == 1


async def test_blocked_match_disappears(client, session_maker, make_player):
    me, other = await make_player(), await make_player()
    await react(client, other, me)
    await react(client, me, other)
    async with session_maker.begin() as session:
        session.add(Block(blocker_id=other.id, blocked_id=me.id))

    assert (await client.get("/api/matches", headers=me.headers)).json() == []


async def test_reaction_kind_is_validated(client, make_player):
    me, other = await make_player(), await make_player()
    response = await client.post(f"/api/people/{other.id}/react", json={"kind": "superlike"}, headers=me.headers)
    assert response.status_code == 422
    assert ReactionKind.LIKE.value == "like"
