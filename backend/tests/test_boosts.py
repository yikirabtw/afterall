"""Бусты: бесплатные по подписке, лимиты, поднятие в лентах пати и людей."""

from datetime import timedelta

from sqlalchemy import update

from app.db.models import Boost, BoostCredits
from app.domain.time import utcnow


async def boost(client, player, expect: int = 200, **body) -> dict:
    response = await client.post("/api/boosts", json=body, headers=player.headers)
    assert response.status_code == expect, response.text
    return response.json()


async def test_free_plan_has_no_boosts(client, make_player, create_lobby):
    me = await make_player()
    lobby = await create_lobby(me)

    status = (await client.get("/api/boosts", headers=me.headers)).json()
    assert (status["weekly_total"], status["weekly_left"], status["credits"]) == (0, 0, 0)
    result = await boost(client, me, 402, kind="lobby", lobby_id=lobby["id"])
    assert result["detail"] == "boost_needs_purchase"


async def test_boosted_lobby_goes_first_with_mark(client, make_player, create_lobby, set_plan):
    owner, other_owner, viewer = await make_player(), await make_player(), await make_player()
    mine = await create_lobby(owner)
    await create_lobby(other_owner)  # новее — без буста была бы первой
    await set_plan("plus", user_id=owner.id)

    status = await boost(client, owner, kind="lobby", lobby_id=mine["id"])

    assert (status["weekly_left"], str(mine["id"]) in status["lobbies"]) == (0, True)
    items = (await client.get("/api/lobbies", headers=viewer.headers)).json()["items"]
    assert items[0]["id"] == mine["id"] and items[0]["boosted_until"] is not None
    assert items[1]["boosted_until"] is None
    assert len(items) == 2  # поднятая не дублируется в обычном списке
    # Тот же буст ещё раз — нельзя, пока действует; недельные кончились
    assert (await boost(client, owner, 409, kind="lobby", lobby_id=mine["id"]))["detail"] == "boost_already_active"


async def test_boosted_profile_goes_first(client, make_player, set_plan):
    viewer = await make_player()
    plain, boosted = await make_player(), await make_player()
    await set_plan("premium", user_id=boosted.id)

    await boost(client, boosted, kind="profile")

    people = (await client.get("/api/people", headers=viewer.headers, params={"limit": 30})).json()
    assert [p["user_id"] for p in people][0] == boosted.id
    assert people[0]["boosted"] is True and all(not p["boosted"] for p in people[1:])
    assert plain.id in [p["user_id"] for p in people]


async def test_only_own_active_lobby(client, make_player, create_lobby, set_plan):
    owner, stranger = await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await set_plan("premium", user_id=stranger.id)

    assert (await boost(client, stranger, 404, kind="lobby", lobby_id=lobby["id"]))["detail"] == "lobby_not_found"


async def test_daily_limit_and_credits(client, make_player, create_lobby, set_plan, session_maker):
    me = await make_player()
    await set_plan("premium", user_id=me.id)
    lobbies = [await create_lobby(me) for _ in range(2)]
    await boost(client, me, kind="lobby", lobby_id=lobbies[0]["id"])
    await boost(client, me, kind="lobby", lobby_id=lobbies[1]["id"])
    status = await boost(client, me, kind="profile")
    assert (status["weekly_left"], status["today_left"]) == (0, 0)

    # Сутки прошли, недельные кончились — тратится купленный
    async with session_maker.begin() as session:
        await session.execute(update(Boost).values(created_at=utcnow() - timedelta(days=2), ends_at=utcnow()))
        session.add(BoostCredits(user_id=me.id, kind="profile", amount=1))
    status = await boost(client, me, kind="profile")
    assert (status["weekly_left"], status["credits"]) == (0, 0)
    assert status["profile_until"] is not None
