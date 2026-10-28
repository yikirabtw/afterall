"""Онбординг: дата рождения → возрастная группа, анкета, игры, расписание, завершение."""

from datetime import date, timedelta

import pytest
from initdata import USER_ID, auth
from sqlalchemy import select

from app.db.models import Game, GameRank, GameRole, User


def born(age: int) -> str:
    """Дата рождения человека, которому сегодня ровно `age` лет (день рождения 1 января уже прошёл)."""
    return date(date.today().year - age, 1, 1).isoformat()


@pytest.fixture
async def games(session_maker) -> dict[str, int]:
    """Две активные игры с рангами и ролями и одна выключенная. Возвращает id по коротким именам."""
    async with session_maker.begin() as session:
        dota = Game(slug="dota2", name="Dota 2", platforms=["pc"], max_party_size=5)
        dota.ranks = [GameRank(code="herald", name="Рекрут", tier=1), GameRank(code="guardian", name="Страж", tier=2)]
        dota.roles = [GameRole(code="carry", name="Керри", sort_order=0), GameRole(code="mid", name="Мид", sort_order=1)]
        cs2 = Game(slug="cs2", name="Counter-Strike 2", platforms=["pc"], max_party_size=5, has_faceit=True)
        cs2.ranks = [GameRank(code="premier_0", name="Premier до 5 000", tier=1)]
        cs2.roles = [GameRole(code="awp", name="Снайпер", sort_order=0)]
        old = Game(slug="old", name="Старая игра", is_active=False)
        session.add_all([dota, cs2, old])
        await session.flush()
        return {
            "dota": dota.id,
            "herald": dota.ranks[0].id,
            "guardian": dota.ranks[1].id,
            "carry": dota.roles[0].id,
            "mid": dota.roles[1].id,
            "cs2": cs2.id,
            "premier_0": cs2.ranks[0].id,
            "awp": cs2.roles[0].id,
            "old": old.id,
        }


async def me(client) -> dict:
    return (await client.get("/api/me", headers=auth())).json()


# --- Дата рождения ---


@pytest.mark.parametrize(("age", "group"), [(13, "13_15"), (16, "16_17"), (18, "18_plus"), (30, "18_plus")])
async def test_birth_date_sets_age_group(client, age, group):
    response = await client.put("/api/me/birth-date", json={"birth_date": born(age)}, headers=auth())

    assert response.status_code == 200
    assert response.json()["age_group"] == group


async def test_birth_date_can_be_set_only_once(client):
    await client.put("/api/me/birth-date", json={"birth_date": born(16)}, headers=auth())

    response = await client.put("/api/me/birth-date", json={"birth_date": born(20)}, headers=auth())

    assert response.status_code == 409
    assert response.json()["detail"] == "birth_date_already_set"
    assert (await me(client))["age_group"] == "16_17"


async def test_too_young_is_not_saved(client):
    response = await client.put("/api/me/birth-date", json={"birth_date": born(12)}, headers=auth())

    assert response.status_code == 422
    assert response.json()["detail"] == "too_young"
    body = await me(client)
    assert (body["birth_date"], body["age_group"]) == (None, None)


async def test_birth_date_in_future_is_rejected(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = await client.put("/api/me/birth-date", json={"birth_date": tomorrow}, headers=auth())
    assert response.status_code == 422


# --- Анкета ---


async def test_profile_create_and_replace(client):
    response = await client.put(
        "/api/me/profile",
        json={"display_name": "  Аня ", "languages": ["ru", "en", "ru"], "city": "Казань", "play_style": "chill"},
        headers=auth(),
    )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["display_name"] == "Аня"
    assert profile["languages"] == ["ru", "en"]
    assert (profile["city"], profile["play_style"], profile["timezone"]) == ("Казань", "chill", "Europe/Moscow")

    # PUT заменяет анкету целиком: чего нет в запросе — сбрасывается к значению по умолчанию
    response = await client.put("/api/me/profile", json={"display_name": "Анна"}, headers=auth())
    profile = response.json()["profile"]
    assert (profile["display_name"], profile["city"], profile["play_style"]) == ("Анна", None, "balanced")


@pytest.mark.parametrize(
    "body",
    [
        {"display_name": ""},
        {"display_name": "x" * 33},
        {"display_name": "Аня", "timezone": "Mars/Base"},
        {"display_name": "Аня", "languages": []},
        {"display_name": "Аня", "languages": ["russian"]},
        {"display_name": "Аня", "play_style": "pro"},
        {"display_name": "Аня", "country_code": "rus"},
    ],
)
async def test_invalid_profile_is_rejected(client, body):
    response = await client.put("/api/me/profile", json=body, headers=auth())
    assert response.status_code == 422


# --- Игры ---


async def test_save_and_replace_games(client, games):
    response = await client.put(
        "/api/me/games",
        json={
            "games": [
                {
                    "game_id": games["dota"],
                    "rank_id": games["guardian"],
                    "role_ids": [games["mid"], games["carry"]],
                    "in_game_nick": "anya",
                },
                {"game_id": games["cs2"]},
            ]
        },
        headers=auth(),
    )

    assert response.status_code == 200
    dota, cs2 = response.json()["games"]
    assert dota == {
        "game_id": games["dota"],
        "rank_id": games["guardian"],
        "role_ids": [games["carry"], games["mid"]],  # в порядке ролей игры
        "in_game_nick": "anya",
        "faceit_elo": None,
        "is_main": True,  # основная не указана — стала первая
    }
    assert (cs2["game_id"], cs2["is_main"]) == (games["cs2"], False)

    response = await client.put("/api/me/games", json={"games": [{"game_id": games["cs2"]}]}, headers=auth())
    assert [game["game_id"] for game in response.json()["games"]] == [games["cs2"]]


@pytest.mark.parametrize(
    ("choice", "code"),
    [
        ({"game_id": "dota", "rank_id": "premier_0"}, "rank_not_in_game"),
        ({"game_id": "dota", "role_ids": ["awp"]}, "role_not_in_game"),
        ({"game_id": "old"}, "unknown_game"),
    ],
)
async def test_game_choice_must_be_consistent(client, games, choice, code):
    await client.put("/api/me/games", json={"games": [{"game_id": games["cs2"]}]}, headers=auth())
    body = {key: [games[v] for v in value] if isinstance(value, list) else games[value] for key, value in choice.items()}

    response = await client.put("/api/me/games", json={"games": [body]}, headers=auth())

    assert response.status_code == 422
    assert response.json()["detail"] == code
    # Ошибка не должна стирать то, что было сохранено раньше
    assert [game["game_id"] for game in (await me(client))["games"]] == [games["cs2"]]


async def test_unknown_game_id_is_rejected(client, games):
    response = await client.put("/api/me/games", json={"games": [{"game_id": 999}]}, headers=auth())
    assert response.json()["detail"] == "unknown_game"


@pytest.mark.parametrize(
    "body",
    [
        {"games": [{"game_id": 1}, {"game_id": 1}]},
        {"games": [{"game_id": 1, "is_main": True}, {"game_id": 2, "is_main": True}]},
        {"games": [{"game_id": n} for n in range(11)]},
    ],
)
async def test_invalid_games_list_is_rejected(client, body):
    response = await client.put("/api/me/games", json=body, headers=auth())
    assert response.status_code == 422


# --- Расписание ---


async def test_save_and_clear_availability(client):
    slots = [
        {"weekday": 4, "start_minute": 1200, "end_minute": 1440},  # пт 20:00–24:00
        {"weekday": 0, "start_minute": 1140, "end_minute": 1380},  # пн 19:00–23:00
    ]
    response = await client.put("/api/me/availability", json={"slots": slots}, headers=auth())

    assert response.status_code == 200
    assert response.json()["availability"] == [slots[1], slots[0]]  # по дням недели

    response = await client.put("/api/me/availability", json={"slots": []}, headers=auth())
    assert response.json()["availability"] == []


@pytest.mark.parametrize(
    "slots",
    [
        [{"weekday": 0, "start_minute": 600, "end_minute": 720}, {"weekday": 0, "start_minute": 700, "end_minute": 800}],
        [{"weekday": 0, "start_minute": 720, "end_minute": 600}],
        [{"weekday": 7, "start_minute": 0, "end_minute": 60}],
        [{"weekday": 0, "start_minute": 0, "end_minute": 1441}],
    ],
)
async def test_invalid_availability_is_rejected(client, slots):
    response = await client.put("/api/me/availability", json={"slots": slots}, headers=auth())
    assert response.status_code == 422


# --- Завершение ---


async def test_complete_reports_what_is_missing(client):
    response = await client.post("/api/me/onboarding/complete", headers=auth())

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "onboarding_incomplete",
        "missing": ["birth_date", "profile", "games"],
    }


async def test_full_onboarding(client, games, session_maker):
    await client.put("/api/me/birth-date", json={"birth_date": born(17)}, headers=auth())
    await client.put("/api/me/profile", json={"display_name": "Аня"}, headers=auth())
    await client.put("/api/me/games", json={"games": [{"game_id": games["dota"]}]}, headers=auth())

    response = await client.post("/api/me/onboarding/complete", headers=auth())

    assert response.status_code == 200
    assert response.json()["is_onboarded"] is True
    async with session_maker() as session:
        first_onboarded_at = (await session.scalar(select(User).where(User.telegram_id == USER_ID))).onboarded_at

    # Повторный вызов ничего не меняет
    response = await client.post("/api/me/onboarding/complete", headers=auth())
    assert response.status_code == 200
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == USER_ID))
    assert user.onboarded_at == first_onboarded_at


# --- FACEIT ---


async def test_faceit_elo_for_cs2(client, games):
    response = await client.put(
        "/api/me/games",
        json={"games": [{"game_id": games["cs2"], "rank_id": games["premier_0"], "faceit_elo": 2150}]},
        headers=auth(),
    )

    assert response.status_code == 200
    [cs2] = response.json()["games"]
    assert (cs2["rank_id"], cs2["faceit_elo"]) == (games["premier_0"], 2150)


async def test_faceit_only_where_supported(client, games):
    response = await client.put(
        "/api/me/games", json={"games": [{"game_id": games["dota"], "faceit_elo": 1500}]}, headers=auth()
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "faceit_not_supported"


@pytest.mark.parametrize("elo", [50, 9999])
async def test_faceit_elo_range(client, games, elo):
    response = await client.put(
        "/api/me/games", json={"games": [{"game_id": games["cs2"], "faceit_elo": elo}]}, headers=auth()
    )
    assert response.status_code == 422


async def test_games_list_says_where_faceit_is(client, games):
    response = await client.get("/api/games", headers=auth())
    assert {game["slug"]: game["has_faceit"] for game in response.json()} == {"dota2": False, "cs2": True}
