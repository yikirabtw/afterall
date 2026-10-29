"""Тестовые боты в копии (ветка dev на Render) — через её API, как живые люди.

Вход ботов подписывается токеном ТЕСТОВОГО бота (STAGING_BOT_TOKEN в backend/.env, вписываете сами).
Основа проверяет подпись своим токеном и такую не примет — поэтому скрипт физически не может
завести ботов среди живых людей. Локальный API (--base http://127.0.0.1:8000) — токеном из BOT_TOKEN.

Боты — со случайными именами, городами, играми, рангами, одним фото (бесплатный тариф).
Часть из них заранее ставит ♥ человеку с именем из --like: лайкнешь в ответ — будет мэтч и чат.
Часть создаёт пати (живут 3 часа — потом запустите ещё раз с --lobbies-only).

Из папки backend:
  python -m scripts.staging_bots create [--count 40] [--ages 15-22] [--like ИМЯ] [--likes 0.4]
                                        [--lobbies 0.3] [--photos ПАПКА_С_JPG] [--start 0] [--base URL]
  python -m scripts.staging_bots lobbies [--count 40] [--lobbies 0.3]   свежие пати от тех же ботов
  python -m scripts.staging_bots hide    [--count 40]                   убрать ботов из ленты
"""

import argparse
import hashlib
import hmac
import random
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.config import settings
from scripts.demo_profiles import abstract_photo
from scripts.dev_bots import BIOS, CITIES, LOOKING, NAMES, PALETTES, STYLES, headers, random_games

ID_BASE = 1_000_000_300_000  # заведомо несуществующие Telegram ID, не пересекаются с dev_bots
PREFIX = "stage_bot_"
LOBBY_TITLES = ["Катка на вечер", "Го в рейтинг", "Ищу стак", "Спокойная игра", "Апаем ранг", "Фан-катки"]


def signing_key(base: str) -> bytes:
    host = urlsplit(base).hostname
    if host in ("127.0.0.1", "localhost"):
        token = settings.bot_token
    else:
        token = settings.staging_bot_token
        if token is None:
            sys.exit("Нет STAGING_BOT_TOKEN в backend/.env — впишите туда токен тестового бота.")
        if settings.bot_token and token.get_secret_value() == settings.bot_token.get_secret_value():
            sys.exit("STAGING_BOT_TOKEN совпадает с боевым BOT_TOKEN — так ботов можно завести к живым людям. Стоп.")
    if token is None:
        sys.exit("BOT_TOKEN не задан в backend/.env.")
    return hmac.new(b"WebAppData", token.get_secret_value().encode(), hashlib.sha256).digest()


def bot(n: int, ages: tuple[int, int]) -> dict:
    """Всё о боте n — детерминированно: повторный запуск даёт того же бота."""
    rng = random.Random(f"stage-{n}")
    name = rng.choice(NAMES)
    age = rng.randint(*ages)
    today = date.today()
    return {
        "rng": rng,
        "name": name,
        "username": f"{PREFIX}{n}",
        "telegram_id": ID_BASE + n,
        "age": age,
        # 1-е число месяца не позже текущего — день рождения в этом году уже был, возраст ровно age
        "birth": date(today.year - age, rng.randint(1, today.month), 1),
        "profile": {
            "display_name": name,
            "bio": rng.choice(BIOS),
            "play_style": rng.choice(STYLES),
            "looking_for": rng.choice(LOOKING),
            "city": rng.choice(CITIES),
            "has_mic": rng.random() < 0.75,
        },
    }


def photo_files(folder: str | None) -> list[Path]:
    if not folder:
        return []
    files = sorted(Path(folder).glob("*.jpg"))
    if not files:
        sys.exit(f"В папке {folder} нет .jpg")
    return files


def create(base: str, count: int, start: int, ages: tuple[int, int], like: str | None, likes: float,
           lobbies: float, photos: list[Path]) -> None:
    api = f"{base.rstrip('/')}/api"
    key = signing_key(base)
    target_id = None
    with httpx.Client(timeout=90) as client:
        client.get(f"{api}/health").raise_for_status()  # бесплатный сервер может спать — будим
        catalog = None
        for n in range(start, start + count):
            b = bot(n, ages)
            rng = b["rng"]
            h = headers(b["telegram_id"], b["name"], b["username"], key)
            client.get(f"{api}/me", headers=h).raise_for_status()
            client.put(f"{api}/me/birth-date", headers=h, json={"birth_date": b["birth"].isoformat()})  # 409 — уже есть
            client.put(f"{api}/me/profile", headers=h, json=b["profile"]).raise_for_status()
            if catalog is None:
                catalog = {g["slug"]: g for g in client.get(f"{api}/games", headers=h).json()}
            games = random_games(rng, catalog)
            client.put(f"{api}/me/games", headers=h, json={"games": games}).raise_for_status()
            client.post(f"{api}/me/onboarding/complete", headers=h).raise_for_status()

            if rng.random() < 0.9:  # десятая часть — без фото, как бывает у живых
                if photos:
                    data = photos[n % len(photos)].read_bytes()
                else:
                    top, bottom = rng.choice(PALETTES)
                    data = abstract_photo(top, bottom, seed=n)
                # Бесплатно — одно фото; повторный запуск получит 409 — это нормально
                client.post(f"{api}/me/photos", headers=h, files={"file": ("p.jpg", data, "image/jpeg")})

            if like and rng.random() < likes:
                if target_id is None:
                    feed = client.get(f"{api}/people", headers=h, params={"limit": 30}).json()
                    found = next((p for p in feed if p["display_name"].lower() == like.lower()), None)
                    target_id = found["user_id"] if found else None
                if target_id is not None:
                    client.post(f"{api}/people/{target_id}/react", headers=h, json={"kind": "like"})

            if rng.random() < lobbies:
                make_lobby(client, api, h, rng, games)
            print(f"{n + 1 - start}/{count}: {b['name']}, {b['age']}")
    if like and target_id is None:
        print(f"«{like}» не нашёлся в ленте ботов — ♥ не поставлены (имя как в анкете? возраст подходит?)")
    print("Готово.")


def make_lobby(client: httpx.Client, api: str, h: dict, rng: random.Random, games: list[dict]) -> None:
    body = {
        "kind": "game",
        "game_id": games[0]["game_id"],
        "title": rng.choice(LOBBY_TITLES),
        "slots_total": rng.randint(2, 5),
        "need_mic": rng.random() < 0.4,
    }
    client.post(f"{api}/lobbies", headers=h, json=body)  # лимит открытых пати — ответ 409, не страшно


def fresh_lobbies(base: str, count: int, start: int, ages: tuple[int, int], lobbies: float) -> None:
    api = f"{base.rstrip('/')}/api"
    key = signing_key(base)
    made = 0
    with httpx.Client(timeout=90) as client:
        client.get(f"{api}/health").raise_for_status()
        for n in range(start, start + count):
            b = bot(n, ages)
            rng = random.Random(f"lobby-{n}-{date.today()}")
            if rng.random() >= lobbies:
                continue
            h = headers(b["telegram_id"], b["name"], b["username"], key)
            me = client.get(f"{api}/me", headers=h).json()
            if me.get("games"):
                make_lobby(client, api, h, rng, me["games"])
                made += 1
    print(f"Пати создано: {made}.")


def hide(base: str, count: int, start: int, ages: tuple[int, int]) -> None:
    api = f"{base.rstrip('/')}/api"
    key = signing_key(base)
    with httpx.Client(timeout=90) as client:
        for n in range(start, start + count):
            b = bot(n, ages)
            h = headers(b["telegram_id"], b["name"], b["username"], key)
            client.put(f"{api}/me/profile", headers=h, json={**b["profile"], "is_visible": False})
    print(f"Скрыто ботов: {count}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["create", "lobbies", "hide"])
    parser.add_argument("--base", default=settings.staging_url)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--start", type=int, default=0, help="с какого номера (добавить ещё — укажите следующий)")
    parser.add_argument("--ages", default="15-22", help="возраст ботов «от-до»")
    parser.add_argument("--like", help="имя из анкеты человека, которому часть ботов поставит ♥")
    parser.add_argument("--likes", type=float, default=0.4)
    parser.add_argument("--lobbies", type=float, default=0.3, help="доля ботов, которые создают пати")
    parser.add_argument("--photos", help="папка с .jpg для фото ботов (без неё — абстрактные градиенты)")
    args = parser.parse_args()
    low, high = (int(part) for part in args.ages.split("-"))
    ages = (low, high)
    if args.command == "create":
        create(args.base, args.count, args.start, ages, args.like, args.likes, args.lobbies, photo_files(args.photos))
    elif args.command == "lobbies":
        fresh_lobbies(args.base, args.count, args.start, ages, args.lobbies)
    else:
        hide(args.base, args.count, args.start, ages)


if __name__ == "__main__":
    main()
