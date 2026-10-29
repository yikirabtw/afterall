"""Уведомления в боте: кому, когда и с какой кнопкой. Вместо Telegram — запись запросов (фикстура notifier)."""

from datetime import timedelta

from conftest import WEBAPP_URL
from fakes import outbox
from players import Player
from sqlalchemy import update

from app.db.models import User
from app.domain.time import utcnow


async def like(client, a: Player, b: Player) -> dict:
    response = await client.post(f"/api/people/{b.id}/react", json={"kind": "like"}, headers=a.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def away(session_maker, *players: Player) -> None:
    """Люди закрыли приложение 10 минут назад."""
    async with session_maker.begin() as session:
        await session.execute(
            update(User)
            .where(User.id.in_([player.id for player in players]))
            .values(last_seen_at=utcnow() - timedelta(minutes=10))
        )


async def send(client, player: Player, kind: str, ref: int, body: str = "привет") -> None:
    response = await client.post(f"/api/chats/{kind}/{ref}/messages", json={"body": body}, headers=player.headers)
    assert response.status_code == 201, response.text


def button_url(message) -> str:
    return message.reply_markup.inline_keyboard[0][0].web_app.url


async def test_match_notifies_the_one_who_liked_first(client, notifier, make_player):
    me, other = await make_player(), await make_player()
    await like(client, other, me)
    assert outbox(notifier) == []  # лайк без взаимности — молча

    await like(client, me, other)

    [note] = outbox(notifier)
    assert note.chat_id == other.telegram_id
    assert "мэтч" in note.text and "Игрок" in note.text
    assert button_url(note) == f"{WEBAPP_URL}?open=chat/direct/{me.id}"


async def test_message_notifies_only_away_people_once_until_read(client, notifier, session_maker, make_player):
    me, other = await make_player(), await make_player()
    await like(client, me, other)
    await like(client, other, me)
    notifier.bot.session.requests.clear()

    await send(client, me, "direct", other.id, "сейчас в приложении — уведомление не нужно")
    assert outbox(notifier) == []

    await away(session_maker, other)
    await send(client, me, "direct", other.id, "го в доту <b>сейчас</b>")
    await send(client, me, "direct", other.id, "второе подряд — одним уведомлением")

    [note] = outbox(notifier)
    assert note.chat_id == other.telegram_id
    assert "го в доту &lt;b&gt;сейчас&lt;/b&gt;" in note.text  # что ввели люди — экранировано
    assert button_url(note) == f"{WEBAPP_URL}?open=chat/direct/{me.id}"

    # Прочитал — следующее сообщение снова позовёт
    await client.get(f"/api/chats/direct/{me.id}", headers=other.headers)
    await away(session_maker, other)
    await send(client, me, "direct", other.id, "ну что?")
    assert len(outbox(notifier)) == 2


async def test_lobby_messages_and_decisions(client, notifier, session_maker, world, make_player):
    owner, guest, rejected = await make_player(), await make_player(), await make_player()
    lobby = (
        await client.post(
            "/api/lobbies",
            json={"kind": "game", "game_id": world["dota"], "title": "Катка", "slots_total": 5},
            headers=owner.headers,
        )
    ).json()["id"]

    # Отклик — создателю, с сообщением
    await client.post(f"/api/lobbies/{lobby}/apply", json={"note": "беру керри"}, headers=guest.headers)
    [applied] = outbox(notifier)
    assert applied.chat_id == owner.telegram_id
    assert "Катка" in applied.text and "беру керри" in applied.text
    assert button_url(applied) == f"{WEBAPP_URL}?open=lobby/{lobby}"

    # Решения — откликнувшимся
    await client.post(f"/api/lobbies/{lobby}/members/{guest.id}/accept", headers=owner.headers)
    await client.post(f"/api/lobbies/{lobby}/apply", headers=rejected.headers)
    await client.post(f"/api/lobbies/{lobby}/members/{rejected.id}/decline", headers=owner.headers)
    accepted, _, declined = outbox(notifier)[1:]
    assert accepted.chat_id == guest.telegram_id and "приняли" in accepted.text
    assert button_url(accepted) == f"{WEBAPP_URL}?open=chat/lobby/{lobby}"
    assert declined.chat_id == rejected.telegram_id and "не взяли" in declined.text
    assert button_url(declined) == f"{WEBAPP_URL}?open=feed"

    # Сообщение в чате пати — тем участникам, кого нет в приложении
    notifier.bot.session.requests.clear()
    await away(session_maker, guest)
    await send(client, owner, "lobby", lobby, "стартуем в 20:00")
    [note] = outbox(notifier)
    assert note.chat_id == guest.telegram_id
    assert "в пати «Катка»" in note.text and "стартуем в 20:00" in note.text
    assert button_url(note) == f"{WEBAPP_URL}?open=chat/lobby/{lobby}"
