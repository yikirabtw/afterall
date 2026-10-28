"""Демо-анкеты для проверки внешнего вида ленты — создаются через обычное API сервера.

Боты входят так же, как люди из Telegram: initData подписывается токеном бота из backend/.env.
Telegram ID у ботов заведомо несуществующие (больше триллиона), ники начинаются с demo_.

Из папки backend:
  python -m scripts.demo_profiles create [--base URL] [--like НИК]  создать (повторный запуск безопасен)
  python -m scripts.demo_profiles hide   [--base URL]               скрыть из ленты (анкеты остаются, но их никто не видит)

--like НИК — бот Тимур заранее ставит ♥ человеку с этим ником: лайкнешь в ответ — будет мэтч.
По умолчанию --base — сервер на Render.
"""

import argparse
import hashlib
import hmac
import io
import json
import random
import sys
import time
from urllib.parse import urlencode

import httpx
from PIL import Image, ImageDraw, ImageFilter

from app.config import settings

DEFAULT_BASE = "https://afterall-apcv.onrender.com"

# Все 18+: боты попадают в ленту только своей возрастной группы
PROFILES = [
    {
        "tg_id": 1_000_000_000_101,
        "username": "demo_alisa",
        "birth_date": "2005-03-14",
        "palettes": [("#ff6a88", "#7b2ff7"), ("#ff9a8b", "#ff6a88"), ("#5ee7df", "#b490ca")],
        "profile": {
            "display_name": "Алиса",
            "bio": "Катаю FACEIT вечерами, ищу стак на рейтинг 🎯 Не тильтую, обещаю",
            "play_style": "tryhard",
            "looking_for": "games",
            "city": "Москва",
            "has_mic": True,
            "discord_tag": "alisa_aim",
        },
        "games": [("cs2", "premier_20k", ["awp"], 2300), ("valorant", "diamond", ["duelist"], None)],
    },
    {
        "tg_id": 1_000_000_000_102,
        "username": "demo_timur",
        "birth_date": "2003-08-02",
        "palettes": [("#0ba360", "#3cba92"), ("#30cfd0", "#330867")],
        "profile": {
            "display_name": "Тимур",
            "bio": "Мид или керри, 5к часов в доте. Без токсика, с юмором 😄",
            "play_style": "balanced",
            "looking_for": "both",
            "city": "Казань",
            "has_mic": True,
            "discord_tag": "timur_mid",
        },
        "games": [("dota2", "ancient", ["mid", "carry"], None), ("cs2", "premier_10k", [], 1650)],
    },
    {
        "tg_id": 1_000_000_000_103,
        "username": "demo_sonya",
        "birth_date": "2006-11-20",
        "palettes": [("#f6d365", "#fda085")],
        "profile": {
            "display_name": "Соня",
            "bio": "Строю замки в майне и смотрю кино в дискорде по пятницам 🍿",
            "play_style": "chill",
            "looking_for": "hangout",
            "city": "Санкт-Петербург",
            "has_mic": True,
        },
        "games": [("minecraft", None, [], None), ("valorant", "gold", ["controller"], None)],
    },
    {
        "tg_id": 1_000_000_000_104,
        "username": "demo_danya",
        "birth_date": "2004-05-09",
        "palettes": [],  # без фото — чтобы видеть, как выглядит анкета-заглушка
        "profile": {
            "display_name": "Даня",
            "bio": "Дуэлянт. Голосом не люблю, но в чате отвечаю быстро",
            "play_style": "tryhard",
            "looking_for": "games",
            "city": "Екатеринбург",
            "has_mic": False,
        },
        "games": [("valorant", "diamond", ["duelist"], None), ("cs2", "premier_15k", ["entry"], None)],
    },
]

SECRET = None


def headers(profile: dict) -> dict:
    user = {
        "id": profile["tg_id"],
        "first_name": profile["profile"]["display_name"],
        "username": profile["username"],
        "language_code": "ru",
    }
    fields = {
        "query_id": "demo",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    fields["hash"] = hmac.new(SECRET, data_check_string.encode(), hashlib.sha256).hexdigest()
    return {"Authorization": "tma " + urlencode(fields)}


def abstract_photo(top: str, bottom: str, seed: int) -> bytes:
    """Абстрактная «фотография»: градиент и мягкие пятна света. Без лиц — это демо."""
    width, height = 1080, 1350
    rng = random.Random(seed)
    base = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(base)
    c1, c2 = Image.new("RGB", (1, 1), top).getpixel((0, 0)), Image.new("RGB", (1, 1), bottom).getpixel((0, 0))
    for y in range(height):
        k = y / (height - 1)
        draw.line([(0, y), (width, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3)))
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for _ in range(6):
        radius = rng.randint(140, 380)
        x, y = rng.randint(0, width), rng.randint(0, height)
        glow_draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(255, 255, 255, rng.randint(25, 70)))
    image = Image.alpha_composite(base.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(60))).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


def create(base: str, like_name: str | None) -> None:
    api = f"{base.rstrip('/')}/api"
    with httpx.Client(timeout=90) as client:
        client.get(f"{api}/health")  # бесплатный сервер мог уснуть — будим заранее
        for profile in PROFILES:
            h = headers(profile)
            client.put(f"{api}/me/birth-date", headers=h, json={"birth_date": profile["birth_date"]})  # 409 при повторе
            client.put(f"{api}/me/profile", headers=h, json=profile["profile"]).raise_for_status()
            games = {game["slug"]: game for game in client.get(f"{api}/games", headers=h).json()}
            choices = []
            for index, (slug, rank_code, role_codes, faceit) in enumerate(profile["games"]):
                game = games[slug]
                choices.append(
                    {
                        "game_id": game["id"],
                        "rank_id": next((r["id"] for r in game["ranks"] if r["code"] == rank_code), None),
                        "role_ids": [r["id"] for r in game["roles"] if r["code"] in role_codes],
                        "faceit_elo": faceit,
                        "is_main": index == 0,
                    }
                )
            client.put(f"{api}/me/games", headers=h, json={"games": choices}).raise_for_status()
            me = client.post(f"{api}/me/onboarding/complete", headers=h).json()
            for number, (top, bottom) in enumerate(profile["palettes"][len(me["photos"]) :], start=len(me["photos"])):
                photo = abstract_photo(top, bottom, seed=profile["tg_id"] + number)
                client.post(f"{api}/me/photos", headers=h, files={"file": ("photo.jpg", photo, "image/jpeg")}).raise_for_status()
            print(f"готово: {profile['profile']['display_name']} ({profile['username']})")

        if like_name:
            timur = headers(PROFILES[1])
            people = client.get(f"{api}/people", headers=timur, params={"limit": 30}).json()
            target = next((p for p in people if p["display_name"].lower() == like_name.lower()), None)
            if target is None:
                print(f"«{like_name}» не найден в ленте Тимура — ♥ не поставлен")
            else:
                client.post(f"{api}/people/{target['user_id']}/react", headers=timur, json={"kind": "like"}).raise_for_status()
                print(f"Тимур поставил ♥: {target['display_name']}")


def hide(base: str) -> None:
    api = f"{base.rstrip('/')}/api"
    with httpx.Client(timeout=90) as client:
        for profile in PROFILES:
            body = {**profile["profile"], "is_visible": False}
            response = client.put(f"{api}/me/profile", headers=headers(profile), json=body)
            print(f"{profile['profile']['display_name']}: {'скрыт' if response.is_success else response.text}")


def main() -> None:
    global SECRET
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["create", "hide"])
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--like", dest="like_name")
    args = parser.parse_args()
    if settings.bot_token is None:
        sys.exit("BOT_TOKEN не задан в backend/.env.")
    SECRET = hmac.new(b"WebAppData", settings.bot_token.get_secret_value().encode(), hashlib.sha256).digest()
    if args.command == "create":
        create(args.base, args.like_name)
    else:
        hide(args.base)


if __name__ == "__main__":
    main()
