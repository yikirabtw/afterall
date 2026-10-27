"""API: вход по initData и первые эндпоинты."""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode

import pytest
from initdata import USER_ID, auth, make_init_data
from sqlalchemy import select

from app.db.models import Game, GameRank, User


async def test_health_needs_no_auth(client):
    response = await client.get("/api/health")
    assert response.json() == {"status": "ok"}


async def test_login_registers_user(client, session_maker):
    response = await client.get("/api/me", headers=auth(make_init_data()))

    assert response.status_code == 200
    body = response.json()
    assert (body["telegram_id"], body["first_name"], body["username"]) == (USER_ID, "Аня", "anya")
    assert body["is_onboarded"] is False
    assert body["profile"] is None
    async with session_maker() as session:
        [user] = await session.scalars(select(User))
    assert user.telegram_id == USER_ID


async def test_second_login_updates_same_user(client, session_maker):
    await client.get("/api/me", headers=auth(make_init_data()))
    response = await client.get("/api/me", headers=auth(make_init_data(first_name="Анна")))

    assert response.json()["first_name"] == "Анна"
    async with session_maker() as session:
        assert len(list(await session.scalars(select(User)))) == 1


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer abc"}, {"Authorization": "tma "}])
async def test_missing_init_data(client, headers):
    response = await client.get("/api/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_init_data"
    assert response.headers["WWW-Authenticate"] == "tma"


async def test_tampered_init_data_is_rejected(client):
    fields = dict(parse_qsl(make_init_data()))
    user = json.loads(fields["user"])
    user["id"] = 999  # пытаемся войти под чужим аккаунтом, оставив старую подпись
    fields["user"] = json.dumps(user)

    response = await client.get("/api/me", headers=auth(urlencode(fields)))

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_init_data"


async def test_init_data_from_another_bot_is_rejected(client):
    response = await client.get("/api/me", headers=auth(make_init_data(token="43:OTHER")))

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_init_data"


async def test_expired_init_data_is_rejected(client):
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    response = await client.get("/api/me", headers=auth(make_init_data(auth_date=two_days_ago)))

    assert response.status_code == 401
    assert response.json()["detail"] == "init_data_expired"


async def test_banned_user_gets_403(client, session_maker):
    async with session_maker.begin() as session:
        session.add(User(telegram_id=USER_ID, first_name="Аня", is_banned=True))

    response = await client.get("/api/me", headers=auth(make_init_data()))

    assert response.status_code == 403
    assert response.json()["detail"] == "banned"


async def test_games_list(client, session_maker):
    async with session_maker.begin() as session:
        game = Game(slug="dota2", name="Dota 2", platforms=["pc"], max_party_size=5)
        # Ранги добавлены не по порядку — API должен отдать их отсортированными
        game.ranks = [GameRank(code="guardian", name="Страж", tier=2), GameRank(code="herald", name="Рекрут", tier=1)]
        session.add_all([game, Game(slug="old", name="Старая игра", is_active=False)])

    response = await client.get("/api/games", headers=auth(make_init_data()))

    assert response.status_code == 200
    [dota] = response.json()
    assert dota["slug"] == "dota2"
    assert [rank["code"] for rank in dota["ranks"]] == ["herald", "guardian"]


async def test_games_need_auth(client):
    response = await client.get("/api/games")
    assert response.status_code == 401


@pytest.mark.parametrize(("origin", "allowed"), [("https://app.example", True), ("https://evil.example", False)])
async def test_cors(client, origin, allowed):
    response = await client.options(
        "/api/me",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"},
    )
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed
