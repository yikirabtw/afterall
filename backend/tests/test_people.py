"""Лента людей: кого видно, «Совпадение N%», лайки, пропуски и мэтчи с контактами."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.db.enums import AgeGroup, LookingFor, PlayStyle, ReactionKind
from app.db.models import Block, Reaction
from app.domain.age import can_meet, search_limits
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


async def test_feed_hides_other_ages_hidden_and_banned(client, make_player):
    me = await make_player()
    peer = await make_player()
    await make_player(AgeGroup.ADULT)
    await make_player(visible=False)
    await make_player(banned=True)

    people = await feed(client, me)

    assert [person["user_id"] for person in people] == [peer.id]
    assert "username" not in people[0] and "discord_tag" not in people[0]  # контактов в ленте нет


# --- Возраст поиска ---


async def ids(client, player) -> set[int]:
    return {person["user_id"] for person in await feed(client, player, limit=30)}


def test_search_limits():
    assert search_limits(13) == search_limits(15) == (13, 17)
    assert search_limits(16) == (13, 20)
    assert search_limits(17) == (13, 21)
    assert search_limits(18) == (16, None)
    assert search_limits(21) == (17, None)
    assert search_limits(30) == (18, None)


def test_age_rules_are_symmetric_and_keep_adults_from_under_16():
    for a in range(13, 61):
        for b in range(13, 61):
            assert can_meet(a, b) == can_meet(b, a)
            young, old = min(a, b), max(a, b)
            if young < 18:
                # Хоть один младше 18 — разница до 4 лет; взрослый и младше 16 — никогда
                assert can_meet(a, b) == (old - young <= 4 and not (old >= 18 and young < 16))
            else:
                assert can_meet(a, b)  # между взрослыми рамок нет — только их собственный выбор


async def test_feed_respects_age_limits(client, make_player):
    p = {age: await make_player(age=age) for age in (13, 15, 17, 18, 21, 22, 40)}

    assert await ids(client, p[17]) == {p[13].id, p[15].id, p[18].id, p[21].id}
    assert await ids(client, p[15]) == {p[13].id, p[17].id}
    assert await ids(client, p[18]) == {p[17].id, p[21].id, p[22].id, p[40].id}
    assert await ids(client, p[40]) == {p[18].id, p[21].id, p[22].id}


async def test_chosen_age_range_works_both_ways(client, make_player):
    me = await make_player(age=20, search_age=(18, 22))
    peer = await make_player(age=21)
    older = await make_player(age=30)
    picky = await make_player(age=22, search_age=(25, None))

    assert await ids(client, me) == {peer.id}
    # Я не в выборе у picky, а older — не в моём: друг другу не показываемся
    assert me.id not in await ids(client, older)
    assert me.id not in await ids(client, picky)
    # Лайк мимо выбора тоже не проходит
    response = await client.post(f"/api/people/{older.id}/react", json={"kind": "like"}, headers=me.headers)
    assert response.status_code == 404


async def test_save_search_age(client, make_player):
    me = await make_player(age=17)

    response = await client.put("/api/me/search-age", json={"age_min": 15, "age_max": 21}, headers=me.headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["search_age_limits"] == {"min": 13, "max": 21}
    # Граница, совпавшая с рамкой, хранится как «до рамки» — и сдвинется вместе с возрастом
    assert (body["profile"]["search_age_min"], body["profile"]["search_age_max"]) == (15, None)
    for wrong in ({"age_min": 12}, {"age_max": 22}, {"age_min": 20, "age_max": 18}):
        response = await client.put("/api/me/search-age", json=wrong, headers=me.headers)
        assert (response.status_code, response.json()["detail"]) == (422, "search_age_out_of_range")


async def test_adult_cannot_choose_under_16(client, make_player):
    me = await make_player(age=25)

    response = await client.put("/api/me/search-age", json={"age_min": 15}, headers=me.headers)
    assert response.status_code == 422
    response = await client.put("/api/me/search-age", json={"age_min": 20, "age_max": None}, headers=me.headers)
    body = response.json()
    assert body["search_age_limits"] == {"min": 18, "max": None}
    assert (body["profile"]["search_age_min"], body["profile"]["search_age_max"]) == (20, None)


async def test_outdated_choice_resets_after_birthday(client, make_player):
    me = await make_player(age=18, search_age=(13, 15))  # выбор остался с 15 лет — теперь он вне рамок
    peer = await make_player(age=19)

    assert await ids(client, me) == {peer.id}
    assert me.id in await ids(client, peer)  # и самого его снова видно


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
    # Ник в Telegram скрыт, пока человек сам не разрешит (test_chats); Discord — виден
    assert (match["user_id"], match["username"], match["discord_tag"]) == (other.id, None, f"{other.username}_dc")
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


async def test_deleted_match_disappears_for_both_and_does_not_come_back(client, make_player):
    me, other = await make_player(), await make_player()
    await react(client, other, me)
    await react(client, me, other)

    response = await client.delete(f"/api/matches/{other.id}", headers=me.headers)

    assert response.status_code == 204
    assert (await client.get("/api/matches", headers=me.headers)).json() == []
    assert (await client.get("/api/matches", headers=other.headers)).json() == []
    # Удалённый не вернётся в ленту, а его повторный лайк не создаст мэтч заново
    assert await feed(client, me) == []
    assert (await react(client, other, me))["match"] is None
    assert (await client.get("/api/matches", headers=me.headers)).json() == []


async def test_delete_unknown_match_is_404(client, make_player):
    me, other = await make_player(), await make_player()
    await react(client, me, other)  # лайк без взаимности — ещё не мэтч

    response = await client.delete(f"/api/matches/{other.id}", headers=me.headers)
    assert (response.status_code, response.json()["detail"]) == (404, "match_not_found")


async def test_reaction_kind_is_validated(client, make_player):
    me, other = await make_player(), await make_player()
    for kind in ("superlike", "unmatch"):  # «unmatch» ставит только удаление мэтча
        response = await client.post(f"/api/people/{other.id}/react", json={"kind": kind}, headers=me.headers)
        assert response.status_code == 422
    assert ReactionKind.LIKE.value == "like"


def test_close_faceit_counts_as_close_rank():
    names = {2: "CS2"}
    # Ранги Premier далеко друг от друга, зато FACEIT почти одинаковый
    me = traits(games={2: 1}, main_game_id=2, faceit={2: 2100})
    close = compatibility(me, traits(games={2: 7}, main_game_id=2, faceit={2: 2250}), names)
    far = compatibility(me, traits(games={2: 7}, main_game_id=2, faceit={2: 1200}), names)

    assert "Близкий FACEIT в CS2" in close.reasons
    assert close.score - far.score == 10


async def test_feed_shows_faceit(client, make_player, world, session_maker):
    from sqlalchemy import update

    from app.db.models import UserGame

    me = await make_player(games={"cs2": "p0"})
    other = await make_player(games={"cs2": "p0"})
    async with session_maker.begin() as session:
        await session.execute(update(UserGame).where(UserGame.user_id == other.id).values(faceit_elo=1800))

    [person] = await feed(client, me)
    assert person["games"][0]["faceit_elo"] == 1800


# --- Кого ищу ---


def test_mode_weights_sum_to_100():
    from app.domain.people import WEIGHTS

    for mode, w in WEIGHTS.items():
        total = w["games_max"] + w["main"] + w["rank"] + w["style"] + w["looking"] + w["language"] + w["mic"]
        assert total == 100, mode


def test_play_mode_values_rank_chat_mode_values_character():
    names = {1: "Dota 2"}
    me = traits(looking_for=LookingFor.BOTH)
    gamer = traits(games={1: 3}, play_style=PlayStyle.TRYHARD, looking_for=LookingFor.GAMES)
    talker = traits(games={}, main_game_id=None, looking_for=LookingFor.BOTH)

    assert compatibility(me, gamer, names, "play").score > compatibility(me, talker, names, "play").score
    assert compatibility(me, talker, names, "chat").score > compatibility(me, gamer, names, "chat").score
    # В «Поболтать» первая причина — про характер, а не про игры
    assert compatibility(me, talker, names, "chat").reasons[0] == "Один стиль — чилл"


async def test_feed_modes_filter_people(client, make_player, world):
    me = await make_player(games={"dota": "guardian"}, looking_for=LookingFor.BOTH)
    gamer = await make_player(games={"dota": "crusader"}, looking_for=LookingFor.GAMES)
    other_game = await make_player(games={"cs2": None}, looking_for=LookingFor.GAMES)
    talker = await make_player(games={"cs2": None}, looking_for=LookingFor.HANGOUT)

    async def ids(mode):
        people = (await client.get("/api/people", params={"mode": mode, "limit": 30}, headers=me.headers)).json()
        return {p["user_id"] for p in people}

    assert await ids("play") == {gamer.id}  # общая игра и ищет игры
    assert await ids("chat") == {talker.id}  # ищет общение
    assert await ids("friends") == {gamer.id, other_game.id, talker.id}
    response = await client.get("/api/people", params={"mode": "party"}, headers=me.headers)
    assert response.status_code == 422

