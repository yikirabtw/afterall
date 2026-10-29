"""Чаты: личные после мэтча и общие у пати; кто может писать, непрочитанные, ограничения."""

from datetime import timedelta

from players import Player
from sqlalchemy import update

from app.db.models import Block, Lobby, Profile
from app.domain.chats import RATE_LIMIT
from app.domain.time import utcnow


async def match(client, a: Player, b: Player) -> None:
    for x, y in ((a, b), (b, a)):
        response = await client.post(f"/api/people/{y.id}/react", json={"kind": "like"}, headers=x.headers)
        assert response.status_code == 200, response.text


async def send(client, player: Player, kind: str, ref: int, body: str = "привет", expect: int = 201) -> dict:
    response = await client.post(f"/api/chats/{kind}/{ref}/messages", json={"body": body}, headers=player.headers)
    assert response.status_code == expect, response.text
    return response.json()


async def read(client, player: Player, kind: str, ref: int, **params) -> dict:
    response = await client.get(f"/api/chats/{kind}/{ref}", params=params, headers=player.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def chats(client, player: Player) -> list[dict]:
    return (await client.get("/api/chats", headers=player.headers)).json()


async def lobby_with(client, world, owner: Player, *guests: Player) -> int:
    lobby = (
        await client.post(
            "/api/lobbies",
            json={"kind": "game", "game_id": world["dota"], "title": "Катка", "slots_total": 5},
            headers=owner.headers,
        )
    ).json()
    for guest in guests:
        await client.post(f"/api/lobbies/{lobby['id']}/apply", headers=guest.headers)
        await client.post(f"/api/lobbies/{lobby['id']}/members/{guest.id}/accept", headers=owner.headers)
    return lobby["id"]


# --- Личные чаты ---


async def test_direct_chat_after_match(client, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)

    sent = await send(client, me, "direct", other.id, "  го в доту?  ")
    assert (sent["body"], sent["mine"], sent["sender_id"]) == ("го в доту?", True, me.id)

    # Собеседник видит непрочитанное, пока не открыл чат
    [summary] = await chats(client, other)
    assert (summary["kind"], summary["ref"], summary["unread"]) == ("direct", me.id, 1)
    assert summary["last_message"]["body"] == "го в доту?"
    assert summary["last_message"]["mine"] is False

    opened = await read(client, other, "direct", me.id)
    assert [(m["body"], m["mine"], m["sender_name"]) for m in opened["messages"]] == [("го в доту?", False, "Игрок 1")]
    assert (opened["title"], opened["can_send"]) == ("Игрок 1", True)
    assert (await chats(client, other))[0]["unread"] == 0
    # Своё сообщение непрочитанным не считается
    assert (await chats(client, me))[0]["unread"] == 0


async def test_new_match_is_in_list_without_messages(client, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)

    [summary] = await chats(client, me)
    assert (summary["ref"], summary["last_message"], summary["unread"]) == (other.id, None, 0)
    assert (await read(client, me, "direct", other.id))["messages"] == []


async def test_cannot_write_without_match(client, make_player):
    me, stranger = await make_player(), await make_player()
    await client.post(f"/api/people/{stranger.id}/react", json={"kind": "like"}, headers=me.headers)  # лайк без взаимности

    assert (await send(client, me, "direct", stranger.id, expect=404))["detail"] == "chat_not_found"
    response = await client.get(f"/api/chats/direct/{stranger.id}", headers=me.headers)
    assert response.json()["detail"] == "chat_not_found"
    assert await chats(client, me) == []


async def test_block_closes_direct_chat(client, session_maker, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)
    await send(client, me, "direct", other.id)
    async with session_maker.begin() as session:
        session.add(Block(blocker_id=other.id, blocked_id=me.id))

    assert await chats(client, me) == []
    assert (await send(client, me, "direct", other.id, expect=404))["detail"] == "chat_not_found"


async def test_polling_and_older_pages(client, make_player, monkeypatch):
    from app.api.routes import chats as chats_route

    monkeypatch.setattr(chats_route, "PAGE_SIZE", 3)
    me, other = await make_player(), await make_player()
    await match(client, me, other)
    ids = [(await send(client, me, "direct", other.id, f"№{n}"))["id"] for n in range(5)]

    latest = await read(client, other, "direct", me.id)
    assert ([m["body"] for m in latest["messages"]], latest["has_more"]) == (["№2", "№3", "№4"], True)
    older = await read(client, other, "direct", me.id, before=ids[2])
    assert ([m["body"] for m in older["messages"]], older["has_more"]) == (["№0", "№1"], False)
    # Опрос: только новее последнего известного
    await send(client, other, "direct", me.id, "ответ")
    fresh = await read(client, me, "direct", other.id, after=ids[-1])
    assert [m["body"] for m in fresh["messages"]] == ["ответ"]


async def test_message_validation_and_rate_limit(client, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)

    assert (await client.post(f"/api/chats/direct/{other.id}/messages", json={"body": "   "}, headers=me.headers)).status_code == 422
    assert (
        await client.post(f"/api/chats/direct/{other.id}/messages", json={"body": "a" * 1001}, headers=me.headers)
    ).status_code == 422
    for _ in range(RATE_LIMIT):
        await send(client, me, "direct", other.id)
    assert (await send(client, me, "direct", other.id, expect=429))["detail"] == "too_many_messages"


# --- Чат пати ---


async def test_lobby_chat_for_accepted_members_only(client, world, make_player):
    owner, guest, applicant = await make_player(), await make_player(), await make_player()
    lobby_id = await lobby_with(client, world, owner, guest)
    await client.post(f"/api/lobbies/{lobby_id}/apply", headers=applicant.headers)  # ещё не принят

    await send(client, owner, "lobby", lobby_id, "собираемся в 20:00")
    await send(client, guest, "lobby", lobby_id, "буду")

    history = await read(client, owner, "lobby", lobby_id)
    assert [(m["sender_name"], m["body"], m["mine"]) for m in history["messages"]] == [
        ("Игрок 1", "собираемся в 20:00", True),
        ("Игрок 2", "буду", False),
    ]
    assert (history["title"], history["game_id"]) == ("Катка", world["dota"])
    assert [(c["kind"], c["ref"], c["unread"]) for c in await chats(client, guest)] == [("lobby", lobby_id, 0)]
    assert (await send(client, applicant, "lobby", lobby_id, expect=404))["detail"] == "chat_not_found"
    assert await chats(client, applicant) == []


async def test_finished_lobby_chat_is_read_only(client, session_maker, world, make_player):
    owner, guest = await make_player(), await make_player()
    lobby_id = await lobby_with(client, world, owner, guest)
    await send(client, guest, "lobby", lobby_id, "gg")
    async with session_maker.begin() as session:
        await session.execute(update(Lobby).where(Lobby.id == lobby_id).values(expires_at=utcnow() - timedelta(minutes=1)))

    history = await read(client, owner, "lobby", lobby_id)
    assert ([m["body"] for m in history["messages"]], history["can_send"]) == (["gg"], False)
    assert (await send(client, owner, "lobby", lobby_id, expect=409))["detail"] == "chat_closed"


# --- Ник в Telegram ---


async def test_telegram_nick_only_when_allowed(client, session_maker, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)

    [hidden] = (await client.get("/api/matches", headers=me.headers)).json()
    assert (hidden["username"], hidden["discord_tag"]) == (None, f"{other.username}_dc")

    async with session_maker.begin() as session:
        await session.execute(update(Profile).where(Profile.user_id == other.id).values(show_telegram=True))
    [shown] = (await client.get("/api/matches", headers=me.headers)).json()
    assert shown["username"] == other.username


async def test_deleting_match_deletes_direct_chat(client, make_player):
    me, other = await make_player(), await make_player()
    await match(client, me, other)
    await send(client, me, "direct", other.id)

    assert (await client.delete(f"/api/matches/{me.id}", headers=other.headers)).status_code == 204

    assert await chats(client, me) == []
    assert await chats(client, other) == []
    for player, ref in ((me, other.id), (other, me.id)):
        response = await client.get(f"/api/chats/direct/{ref}", headers=player.headers)
        assert response.status_code == 404
