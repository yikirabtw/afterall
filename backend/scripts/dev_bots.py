"""Боты для разработки ленты — только локально (127.0.0.1 и dev.db), на сервер не ходят.

Создаются через обычное API, как живые люди: случайные имена, города, игры, ранги, роли, FACEIT, стиль,
фото (абстрактные градиенты) или без фото. Возраст — в группе тестового пользователя dev_tester,
чтобы он их видел. Часть ботов заранее ставит ему ♥ — лайкнешь в ответ, будет мэтч и чат.

Из папки backend (локальный API должен быть запущен):
  python -m scripts.dev_bots create [--count 60] [--likes 0.3]   добавить ботов (нумерация продолжается)
  python -m scripts.dev_bots reset                                лента заново: забыть лайки/пропуски dev_tester
  python -m scripts.dev_bots remove                               удалить всех ботов (каскадом — их пати и чаты)
"""

import argparse
import hashlib
import hmac
import json
import random
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.config import settings
from scripts.demo_profiles import abstract_photo

API = "http://127.0.0.1:8000/api"
DB = Path(__file__).resolve().parent.parent / "dev.db"
TESTER = "dev_tester"
ID_BASE = 1_000_000_100_000  # заведомо несуществующие Telegram ID
PREFIX = "dev_bot_"

NAMES = [
    "Артём", "Максим", "Лёша", "Ваня", "Кирилл", "Егор", "Никита", "Миша", "Дима", "Саша", "Гоша", "Рома",
    "Лера", "Аня", "Катя", "Маша", "Полина", "Вика", "Даша", "Настя", "Ксюша", "Алина", "Ева", "Милана",
    "Тёма", "Влад", "Женя", "Лиза", "Соня", "Ульяна",
]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Самара", "Краснодар", "Пермь", None]
BIOS = [
    "Ищу стак на вечер, без токсика 🙌",
    "Играю после учёбы, люблю тактику",
    "Тильтую редко, шучу часто",
    "Хочу апнуть ранг до конца сезона",
    "Просто покатать и поболтать",
    "Саппорт по жизни, спасаю всех",
    "Ночной игрок 🌙 после 22:00",
    "Ищу друзей для майна и не только",
    None,
]
PALETTES = [
    ("#ff6a88", "#7b2ff7"), ("#5ee7df", "#b490ca"), ("#0ba360", "#3cba92"), ("#f6d365", "#fda085"),
    ("#30cfd0", "#330867"), ("#a1c4fd", "#c2e9fb"), ("#2b2b2b", "#8a8a8a"), ("#e0e0e0", "#3a3a3a"),
]
STYLES = ["chill", "balanced", "tryhard"]
LOOKING = ["games", "hangout", "both"]
# Возраст внутри группы — по нему считается дата рождения
AGES = {"13_15": (13, 15), "16_17": (16, 17), "18_plus": (18, 30)}


def local_only() -> sqlite3.Connection:
    if not settings.database_url.startswith("sqlite"):
        sys.exit("Скрипт только для локальной SQLite-базы.")
    return sqlite3.connect(DB)


def secret() -> bytes:
    if settings.bot_token is None:
        sys.exit("BOT_TOKEN не задан в backend/.env.")
    return hmac.new(b"WebAppData", settings.bot_token.get_secret_value().encode(), hashlib.sha256).digest()


def headers(tg_id: int, name: str, username: str, key: bytes) -> dict:
    user = {"id": tg_id, "first_name": name, "username": username, "language_code": "ru"}
    fields = {
        "query_id": "dev",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    fields["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return {"Authorization": "tma " + urlencode(fields)}


def tester(db: sqlite3.Connection) -> tuple[int, str]:
    row = db.execute("select id, age_group from users where username = ?", (TESTER,)).fetchone()
    if not row or not row[1]:
        sys.exit(f"Нет пользователя {TESTER} с датой рождения — сначала пройди онбординг в браузере.")
    return row[0], row[1]


def random_games(rng: random.Random, catalog: dict) -> list[dict]:
    picked = rng.sample(list(catalog.values()), rng.randint(1, min(3, len(catalog))))
    choices = []
    for index, game in enumerate(picked):
        rank = rng.choice(game["ranks"])["id"] if game["ranks"] and rng.random() < 0.85 else None
        roles = [r["id"] for r in rng.sample(game["roles"], rng.randint(0, min(2, len(game["roles"]))))] if game["roles"] else []
        faceit = rng.randint(400, 3200) if game["has_faceit"] and rng.random() < 0.6 else None
        choices.append({"game_id": game["id"], "rank_id": rank, "role_ids": roles, "faceit_elo": faceit, "is_main": index == 0})
    return choices


def create(count: int, likes: float) -> None:
    db = local_only()
    tester_id, group = tester(db)
    key = secret()
    start = db.execute("select count(*) from users where username like ?", (PREFIX + "%",)).fetchone()[0]
    low, high = AGES[group]
    today = date.today()
    with httpx.Client(timeout=30) as client:
        client.get(f"{API}/health").raise_for_status()
        catalog = None
        for n in range(start, start + count):
            rng = random.Random(n)
            name = rng.choice(NAMES)
            h = headers(ID_BASE + n, name, f"{PREFIX}{n}", key)
            age = rng.randint(low, high)
            # 1-е число месяца не позже текущего — день рождения в этом году уже был, возраст ровно age
            birth = date(today.year - age, rng.randint(1, today.month), 1)
            client.put(f"{API}/me/birth-date", headers=h, json={"birth_date": birth.isoformat()})
            profile = {
                "display_name": name,
                "bio": rng.choice(BIOS),
                "play_style": rng.choice(STYLES),
                "looking_for": rng.choice(LOOKING),
                "city": rng.choice(CITIES),
                "has_mic": rng.random() < 0.75,
            }
            client.put(f"{API}/me/profile", headers=h, json=profile).raise_for_status()
            if catalog is None:
                catalog = {g["slug"]: g for g in client.get(f"{API}/games", headers=h).json()}
            client.put(f"{API}/me/games", headers=h, json={"games": random_games(rng, catalog)}).raise_for_status()
            client.post(f"{API}/me/onboarding/complete", headers=h).raise_for_status()
            for i in range(rng.choice([0, 1, 1, 2, 3])):
                top, bottom = rng.choice(PALETTES)
                photo = abstract_photo(top, bottom, seed=n * 10 + i)
                client.post(f"{API}/me/photos", headers=h, files={"file": ("p.jpg", photo, "image/jpeg")}).raise_for_status()
            if rng.random() < likes:
                client.post(f"{API}/people/{tester_id}/react", headers=h, json={"kind": "like"})
            print(f"{n + 1 - start}/{count}: {name}, {age}")
    print(f"Готово: ботов в базе — {start + count}.")


def reset() -> None:
    db = local_only()
    tester_id, _ = tester(db)
    gone = db.execute("delete from reactions where from_user_id = ?", (tester_id,)).rowcount
    db.commit()
    print(f"Забыто реакций {TESTER}: {gone}. Лента начнётся заново (мэтчи остались).")


def remove() -> None:
    db = local_only()
    db.execute("pragma foreign_keys = on")
    gone = db.execute("delete from users where username like ?", (PREFIX + "%",)).rowcount
    db.commit()
    print(f"Удалено ботов: {gone}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["create", "reset", "remove"])
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--likes", type=float, default=0.3, help="доля ботов, которые заранее лайкают dev_tester")
    args = parser.parse_args()
    if args.command == "create":
        create(args.count, args.likes)
    elif args.command == "reset":
        reset()
    else:
        remove()


if __name__ == "__main__":
    main()
