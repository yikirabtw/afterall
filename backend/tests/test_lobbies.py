"""Пати: создание, лента и её фильтры, видимость, отклики и решения создателя."""

from datetime import datetime, timedelta, timezone

import pytest
from initdata import auth
from players import Player
from sqlalchemy import update

from app.db.enums import AgeGroup
from app.db.models import Block, Lobby, User
from app.domain.time import utcnow


@pytest.fixture
def create_lobby(client, world):
    async def _create(owner: Player, expect: int = 201, **overrides) -> dict:
        body = {"kind": "game", "game_id": "dota", "title": "Нужен саппорт", "slots_total": 3}
        body.update(overrides)
        # В тестах игры и ранги задаём короткими именами — подставляем id
        for key in ("game_id", "rank_min_id", "rank_max_id"):
            if isinstance(body.get(key), str):
                body[key] = world[body[key]]
        response = await client.post("/api/lobbies", json=body, headers=owner.headers)
        assert response.status_code == expect, response.text
        return response.json()

    return _create


async def feed_ids(client, player: Player, **params) -> list[int]:
    response = await client.get("/api/lobbies", params=params, headers=player.headers)
    assert response.status_code == 200, response.text
    return [lobby["id"] for lobby in response.json()["items"]]


async def detail(client, lobby_id: int, player: Player) -> dict:
    return (await client.get(f"/api/lobbies/{lobby_id}", headers=player.headers)).json()


async def act(client, lobby_id: int, player: Player, action: str, member: Player | None = None, **body):
    path = f"/api/lobbies/{lobby_id}/members/{member.id}/{action}" if member else f"/api/lobbies/{lobby_id}/{action}"
    return await client.post(path, json=body or None, headers=player.headers)


async def expire(session_maker, lobby_id: int) -> None:
    async with session_maker.begin() as session:
        await session.execute(
            update(Lobby).where(Lobby.id == lobby_id).values(expires_at=utcnow() - timedelta(minutes=1))
        )


# --- Создание ---


async def test_create_lobby(make_player, create_lobby):
    owner = await make_player()

    lobby = await create_lobby(owner, contact_link="https://discord.gg/abc", need_mic=True)

    assert (lobby["is_owner"], lobby["my_status"], lobby["status"]) == (True, "accepted", "open")
    assert (lobby["slots_total"], lobby["slots_taken"]) == (3, 1)
    assert lobby["contact_link"] == "https://discord.gg/abc"  # создатель видит свою ссылку
    assert [member["user_id"] for member in lobby["members"]] == [owner.id]
    expires_at = datetime.fromisoformat(lobby["expires_at"])
    assert expires_at.tzinfo is not None  # время всегда с часовым поясом
    assert abs(expires_at - (utcnow() + timedelta(hours=3))) < timedelta(minutes=1)


async def test_hangout_lobby_has_no_game(make_player, create_lobby):
    owner = await make_player()
    lobby = await create_lobby(owner, kind="hangout", game_id=None, title="Кино в Discord", slots_total=8)
    assert (lobby["kind"], lobby["game_id"]) == ("hangout", None)


async def test_not_onboarded_user_cannot_create(client):
    response = await client.post(
        "/api/lobbies", json={"kind": "hangout", "title": "Кино", "slots_total": 3}, headers=auth()
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "onboarding_required"


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"slots_total": 6}, "party_too_big"),
        ({"rank_min_id": "p0"}, "rank_not_in_game"),
        ({"rank_min_id": "crusader", "rank_max_id": "herald"}, "invalid_rank_range"),
        ({"game_id": "old"}, "unknown_game"),
        ({"starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()}, "starts_at_out_of_range"),
    ],
)
async def test_create_rejects_inconsistent_lobby(make_player, create_lobby, overrides, code):
    owner = await make_player()
    response = await create_lobby(owner, expect=422, **overrides)
    assert response["detail"] == code


@pytest.mark.parametrize(
    "overrides",
    [
        {"game_id": None},  # игровая пати без игры
        {"kind": "hangout"},  # «просто посидеть», но с игрой
        {"contact_link": "https://evil.example/invite"},
        {"contact_link": "http://t.me/party"},  # только https
        {"contact_link": "https://discord.com/login"},
        {"title": "ok"},
        {"slots_total": 1},
        {"starts_at": "2026-06-01T20:00:00"},  # без часового пояса
    ],
)
async def test_create_rejects_invalid_body(make_player, create_lobby, overrides):
    owner = await make_player()
    await create_lobby(owner, expect=422, **overrides)


async def test_active_lobby_limit(make_player, create_lobby, client):
    owner = await make_player()
    first = await create_lobby(owner)
    await create_lobby(owner)

    response = await create_lobby(owner, expect=409)
    assert response["detail"] == "too_many_active_lobbies"

    await act(client, first["id"], owner, "cancel")
    await create_lobby(owner)


# --- Лента и видимость ---


async def test_feed_shows_only_own_age_group(client, make_player, create_lobby):
    owner = await make_player(AgeGroup.TEEN_16_17)
    peer = await make_player(AgeGroup.TEEN_16_17)
    adult = await make_player(AgeGroup.ADULT)
    lobby = await create_lobby(owner, contact_link="https://t.me/party")

    assert await feed_ids(client, peer) == [lobby["id"]]
    assert await feed_ids(client, adult) == []
    assert await feed_ids(client, owner) == []  # свои — в /mine, а не в ленте
    # Взрослый не может открыть подростковую пати даже по прямой ссылке
    assert (await client.get(f"/api/lobbies/{lobby['id']}", headers=adult.headers)).status_code == 404
    assert (await act(client, lobby["id"], adult, "apply")).status_code == 404


async def test_feed_hides_contacts_and_members(client, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner, contact_link="https://t.me/party")

    [item] = (await client.get("/api/lobbies", headers=peer.headers)).json()["items"]
    assert item["contact_link"] is None
    assert (await detail(client, lobby["id"], peer))["members"] == []


@pytest.mark.parametrize("blocked_by_owner", [True, False])
async def test_blocks_hide_lobby_both_ways(client, session_maker, make_player, create_lobby, blocked_by_owner):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner)
    async with session_maker.begin() as session:
        pair = (owner.id, peer.id) if blocked_by_owner else (peer.id, owner.id)
        session.add(Block(blocker_id=pair[0], blocked_id=pair[1]))

    assert await feed_ids(client, peer) == []
    assert (await client.get(f"/api/lobbies/{lobby['id']}", headers=peer.headers)).status_code == 404


async def test_banned_owner_lobby_is_hidden(client, session_maker, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    await create_lobby(owner)
    async with session_maker.begin() as session:
        await session.execute(update(User).where(User.id == owner.id).values(is_banned=True))

    assert await feed_ids(client, peer) == []


async def test_expired_and_cancelled_lobbies_leave_feed(client, session_maker, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    expired = await create_lobby(owner)
    cancelled = await create_lobby(owner)
    await expire(session_maker, expired["id"])
    await act(client, cancelled["id"], owner, "cancel")

    assert await feed_ids(client, peer) == []
    assert (await detail(client, expired["id"], owner))["status"] == "expired"
    assert (await detail(client, cancelled["id"], owner))["status"] == "cancelled"


async def test_feed_filters(client, make_player, create_lobby):
    owner1, owner2, peer = await make_player(), await make_player(), await make_player()
    dota_chill = await create_lobby(owner1, play_style="chill")
    dota_any = await create_lobby(owner1)
    cs2_tryhard = await create_lobby(owner2, game_id="cs2", play_style="tryhard", language="en")
    hangout = await create_lobby(owner2, kind="hangout", game_id=None, title="Посидеть в Discord")

    world_dota = dota_chill["game_id"]
    assert await feed_ids(client, peer, game_id=world_dota) == [dota_any["id"], dota_chill["id"]]
    assert await feed_ids(client, peer, kind="hangout") == [hangout["id"]]
    assert await feed_ids(client, peer, language="en") == [cs2_tryhard["id"]]
    # Пати без требований к стилю подходят под любой фильтр стиля
    assert await feed_ids(client, peer, play_style="chill") == [hangout["id"], dota_any["id"], dota_chill["id"]]


async def test_feed_fits_me(client, make_player, create_lobby):
    owner1, owner2 = await make_player(), await make_player()
    peer = await make_player(has_mic=False, dota_rank="guardian")
    no_rank = await make_player(dota_rank=None)
    plain = await create_lobby(owner1)
    needs_mic = await create_lobby(owner1, need_mic=True)
    high_rank = await create_lobby(owner2, rank_min_id="crusader")
    my_range = await create_lobby(owner2, rank_min_id="herald", rank_max_id="guardian")

    assert await feed_ids(client, peer) == [my_range["id"], high_rank["id"], needs_mic["id"], plain["id"]]
    assert await feed_ids(client, peer, fits_me=True) == [my_range["id"], plain["id"]]
    # Ранг не указан — пати с требованиями к рангу не подходят
    assert await feed_ids(client, no_rank, fits_me=True) == [needs_mic["id"], plain["id"]]


async def test_feed_pagination(client, make_player, create_lobby):
    owner1, owner2, peer = await make_player(), await make_player(), await make_player()
    ids = [(await create_lobby(owner))["id"] for owner in (owner1, owner1, owner2)]

    first = (await client.get("/api/lobbies", params={"limit": 2}, headers=peer.headers)).json()
    assert [item["id"] for item in first["items"]] == [ids[2], ids[1]]
    second = (
        await client.get("/api/lobbies", params={"limit": 2, "cursor": first["next_cursor"]}, headers=peer.headers)
    ).json()
    assert [item["id"] for item in second["items"]] == [ids[0]]
    assert second["next_cursor"] is None


# --- Отклики и решения создателя ---


async def test_apply_and_accept_reveals_contacts(client, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner, contact_link="https://t.me/party")

    applied = (await act(client, lobby["id"], peer, "apply", note="Играю на саппорте")).json()
    assert (applied["my_status"], applied["contact_link"], applied["members"]) == ("pending", None, [])

    owner_view = await detail(client, lobby["id"], owner)
    applicant = owner_view["members"][1]
    assert (applicant["user_id"], applicant["status"], applicant["note"]) == (peer.id, "pending", "Играю на саппорте")
    assert applicant["rank_id"] is not None  # создатель видит ранг откликнувшегося в этой игре
    assert (applicant["username"], applicant["discord_tag"]) == (None, None)  # контакты — только после принятия

    accepted = (await act(client, lobby["id"], owner, "accept", member=peer)).json()
    assert accepted["slots_taken"] == 2

    peer_view = await detail(client, lobby["id"], peer)
    assert peer_view["contact_link"] == "https://t.me/party"
    assert [(m["user_id"], m["username"], m["discord_tag"]) for m in peer_view["members"]] == [
        (owner.id, owner.username, f"{owner.username}_dc"),
        (peer.id, peer.username, f"{peer.username}_dc"),
    ]


async def test_full_lobby_closes_and_reopens(client, make_player, create_lobby):
    owner, first, second = await make_player(), await make_player(), await make_player()
    lobby = await create_lobby(owner, slots_total=2)
    await act(client, lobby["id"], first, "apply")
    await act(client, lobby["id"], second, "apply")

    full = (await act(client, lobby["id"], owner, "accept", member=first)).json()
    assert full["status"] == "full"
    assert await feed_ids(client, second) == []
    assert (await act(client, lobby["id"], owner, "accept", member=second)).json()["detail"] == "lobby_full"

    reopened = (await act(client, lobby["id"], first, "leave")).json()
    assert (reopened["status"], reopened["my_status"]) == ("open", "left")
    assert (await act(client, lobby["id"], owner, "accept", member=second)).status_code == 200


async def test_declined_and_kicked_cannot_reapply(client, make_player, create_lobby):
    owner, declined, kicked = await make_player(), await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], declined, "apply")
    await act(client, lobby["id"], kicked, "apply")
    await act(client, lobby["id"], owner, "decline", member=declined)
    await act(client, lobby["id"], owner, "accept", member=kicked)

    after_kick = (await act(client, lobby["id"], owner, "kick", member=kicked)).json()
    assert after_kick["slots_taken"] == 1

    assert (await act(client, lobby["id"], declined, "apply")).json()["detail"] == "application_declined"
    assert (await act(client, lobby["id"], kicked, "apply")).json()["detail"] == "kicked_from_lobby"


async def test_withdrawn_application_can_be_sent_again(client, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], peer, "apply")
    await act(client, lobby["id"], peer, "leave")

    again = await act(client, lobby["id"], peer, "apply", note="Передумал")
    assert again.json()["my_status"] == "pending"


@pytest.mark.parametrize(
    ("player_kwargs", "lobby_kwargs", "code"),
    [
        ({"has_mic": False}, {"need_mic": True}, "mic_required"),
        ({"dota_rank": "guardian"}, {"rank_min_id": "crusader"}, "rank_out_of_range"),
        ({"dota_rank": None}, {"rank_max_id": "guardian"}, "rank_out_of_range"),
    ],
)
async def test_apply_checks_requirements(client, make_player, create_lobby, player_kwargs, lobby_kwargs, code):
    owner, peer = await make_player(), await make_player(**player_kwargs)
    lobby = await create_lobby(owner, **lobby_kwargs)

    response = await act(client, lobby["id"], peer, "apply")

    assert response.status_code == 422
    assert response.json()["detail"] == code


async def test_apply_conflicts(client, session_maker, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], peer, "apply")

    assert (await act(client, lobby["id"], peer, "apply")).json()["detail"] == "already_applied"
    assert (await act(client, lobby["id"], owner, "apply")).json()["detail"] == "cannot_apply_own_lobby"
    assert (await act(client, lobby["id"], owner, "leave")).json()["detail"] == "owner_cannot_leave"

    await expire(session_maker, lobby["id"])
    late = await make_player()
    assert (await act(client, lobby["id"], late, "apply")).json()["detail"] == "lobby_not_active"
    assert (await detail(client, lobby["id"], peer))["status"] == "expired"  # откликнувшийся видит, что пати закончилась


async def test_only_owner_decides(client, make_player, create_lobby):
    owner, peer, other = await make_player(), await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], other, "apply")

    response = await act(client, lobby["id"], peer, "accept", member=other)

    assert response.status_code == 403
    assert response.json()["detail"] == "not_lobby_owner"


async def test_owner_actions_need_right_member_state(client, make_player, create_lobby):
    owner, peer, stranger = await make_player(), await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], peer, "apply")
    await act(client, lobby["id"], owner, "accept", member=peer)

    assert (await act(client, lobby["id"], owner, "accept", member=peer)).json()["detail"] == "member_not_pending"
    assert (await act(client, lobby["id"], owner, "accept", member=stranger)).status_code == 404
    assert (await act(client, lobby["id"], owner, "accept", member=owner)).status_code == 404


async def test_pending_applications_limit(client, make_player, create_lobby):
    peer = await make_player()
    lobbies = []
    for _ in range(6):
        owner = await make_player()
        lobbies += [await create_lobby(owner), await create_lobby(owner)]

    for lobby in lobbies[:10]:
        assert (await act(client, lobby["id"], peer, "apply")).status_code == 200
    response = await act(client, lobbies[10]["id"], peer, "apply")
    assert response.json()["detail"] == "too_many_applications"


async def test_my_lobbies(client, make_player, create_lobby):
    owner, peer = await make_player(), await make_player()
    lobby = await create_lobby(owner)
    await act(client, lobby["id"], peer, "apply")

    mine_owner = (await client.get("/api/lobbies/mine", headers=owner.headers)).json()
    mine_peer = (await client.get("/api/lobbies/mine", headers=peer.headers)).json()
    assert [(item["id"], item["is_owner"]) for item in mine_owner] == [(lobby["id"], True)]
    assert [(item["id"], item["my_status"]) for item in mine_peer] == [(lobby["id"], "pending")]

    await act(client, lobby["id"], owner, "cancel")
    assert (await client.get("/api/lobbies/mine", headers=owner.headers)).json() == []
