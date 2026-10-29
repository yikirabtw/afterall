"""Косметика: надеть свою вещь, что видят другие, подарок Premium, выдача админом."""

from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TelegramUser
from conftest import ADMIN_TELEGRAM_ID
from fakes import RecordingSession

from app.bot.dispatcher import build_dispatcher
from app.db.models import UserItem
from app.domain.time import utcnow


async def give(session_maker, player, *items: str) -> None:
    async with session_maker.begin() as session:
        for item in items:
            session.add(UserItem(user_id=player.id, item_id=item, acquired_at=utcnow(), source="admin"))


async def equip(client, player, expect: int = 200, **slots) -> dict:
    response = await client.put("/api/me/equipped", json=slots, headers=player.headers)
    assert response.status_code == expect, response.text
    return response.json()


async def test_equip_own_items_and_others_see_them(client, make_player, session_maker):
    me, viewer = await make_player(), await make_player()
    await give(session_maker, me, "frame-neon", "badge-night", "match-red")

    result = await equip(client, me, frame="frame-neon", badge="badge-night", match="match-red")

    assert result["items"] == ["badge-night", "frame-neon", "match-red"]
    assert result["profile"]["equipped"] == {"frame": "frame-neon", "badge": "badge-night", "match": "match-red"}
    [card] = (await client.get("/api/people", headers=viewer.headers)).json()
    assert card["look"] == {"frame": "frame-neon", "badge": "badge-night"}  # сцена мэтча — только своя


async def test_cannot_equip_foreign_or_wrong_slot(client, make_player, session_maker):
    me = await make_player()
    await give(session_maker, me, "frame-neon")

    assert (await equip(client, me, 422, frame="frame-pixel"))["detail"] == "item_not_owned"
    assert (await equip(client, me, 422, badge="frame-neon"))["detail"] == "item_not_owned"
    assert (await equip(client, me))["profile"]["equipped"] == {}  # всё снять — можно всегда


async def test_premium_gift_once_a_month(client, make_player, set_plan):
    me = await make_player()
    response = await client.post("/api/me/gift", json={"item_id": "bg-smoke"}, headers=me.headers)
    assert (response.status_code, response.json()["detail"]) == (403, "gift_needs_premium")

    await set_plan("premium", user_id=me.id)
    assert (await client.get("/api/me", headers=me.headers)).json()["gift_available"] is True
    result = (await client.post("/api/me/gift", json={"item_id": "bg-smoke"}, headers=me.headers)).json()
    assert "bg-smoke" in result["items"] and result["gift_available"] is False

    again = await client.post("/api/me/gift", json={"item_id": "bg-grid"}, headers=me.headers)
    assert (again.status_code, again.json()["detail"]) == (429, "gift_already_taken")
    owned = await client.post("/api/me/gift", json={"item_id": "bg-smoke"}, headers=me.headers)
    assert owned.status_code == 409


async def test_admin_gives_item(session_maker, make_player, client):
    target = await make_player()
    bot = Bot("42:TEST", session=RecordingSession())
    dispatcher = build_dispatcher(session_maker, None, frozenset({ADMIN_TELEGRAM_ID}))
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=ADMIN_TELEGRAM_ID, type="private"),
            from_user=TelegramUser(id=ADMIN_TELEGRAM_ID, is_bot=False, first_name="Админ"),
            text=f"/item @{target.username} frame-lamp",
        ),
    )

    await dispatcher.feed_update(bot, update)

    me = (await client.get("/api/me", headers=target.headers)).json()
    assert me["items"] == ["frame-lamp"]
