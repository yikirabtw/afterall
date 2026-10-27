"""Заполняет справочник игр. Можно запускать повторно: обновляет игры по slug, ранги и роли по code.

Запуск из папки backend:  python -m scripts.seed_games
Список стартовый — правится после выбора первых игр.
"""

from sqlalchemy import select

from app.db.models import Game, GameRank, GameRole
from app.db.session import SessionLocal

# Ранги — от низшего к высшему, роли — в порядке показа
GAMES = [
    {
        "slug": "cs2",
        "name": "Counter-Strike 2",
        "platforms": ["pc"],
        "max_party_size": 5,
        "ranks": [
            ("premier_0", "Premier до 5 000"),
            ("premier_5k", "Premier 5 000–9 999"),
            ("premier_10k", "Premier 10 000–14 999"),
            ("premier_15k", "Premier 15 000–19 999"),
            ("premier_20k", "Premier 20 000–24 999"),
            ("premier_25k", "Premier 25 000–29 999"),
            ("premier_30k", "Premier 30 000+"),
        ],
        "roles": [
            ("entry", "Энтри"),
            ("awp", "Снайпер"),
            ("support", "Саппорт"),
            ("lurker", "Люркер"),
            ("igl", "Капитан"),
        ],
    },
    {
        "slug": "dota2",
        "name": "Dota 2",
        "platforms": ["pc"],
        "max_party_size": 5,
        "ranks": [
            ("herald", "Рекрут"),
            ("guardian", "Страж"),
            ("crusader", "Рыцарь"),
            ("archon", "Герой"),
            ("legend", "Легенда"),
            ("ancient", "Властелин"),
            ("divine", "Божество"),
            ("immortal", "Титан"),
        ],
        "roles": [
            ("carry", "Керри"),
            ("mid", "Мид"),
            ("offlane", "Оффлейн"),
            ("soft_support", "Саппорт (4)"),
            ("hard_support", "Фулл-саппорт (5)"),
        ],
    },
    {
        "slug": "valorant",
        "name": "Valorant",
        "platforms": ["pc", "console"],
        "max_party_size": 5,
        "ranks": [
            ("iron", "Железо"),
            ("bronze", "Бронза"),
            ("silver", "Серебро"),
            ("gold", "Золото"),
            ("platinum", "Платина"),
            ("diamond", "Алмаз"),
            ("ascendant", "Восхождение"),
            ("immortal", "Бессмертие"),
            ("radiant", "Радиант"),
        ],
        "roles": [
            ("duelist", "Дуэлянт"),
            ("initiator", "Инициатор"),
            ("controller", "Контроллер"),
            ("sentinel", "Страж"),
        ],
    },
    {
        "slug": "standoff2",
        "name": "Standoff 2",
        "platforms": ["mobile"],
        "max_party_size": 5,
        # TODO: сверить названия рангов с актуальной версией игры
        "ranks": [
            ("bronze", "Бронза"),
            ("silver", "Серебро"),
            ("gold", "Золото"),
            ("phoenix", "Феникс"),
            ("ranger", "Рейнджер"),
            ("champion", "Чемпион"),
            ("master", "Мастер"),
            ("elite", "Элита"),
            ("legend", "Легенда"),
        ],
        "roles": [],
    },
    {
        "slug": "brawl_stars",
        "name": "Brawl Stars",
        "platforms": ["mobile"],
        "max_party_size": 3,
        "ranks": [
            ("bronze", "Бронза"),
            ("silver", "Серебро"),
            ("gold", "Золото"),
            ("diamond", "Алмаз"),
            ("mythic", "Мифический"),
            ("legendary", "Легендарный"),
            ("masters", "Мастер"),
            ("pro", "Про"),
        ],
        "roles": [],
    },
    {
        "slug": "fortnite",
        "name": "Fortnite",
        "platforms": ["pc", "console", "mobile"],
        "max_party_size": 4,
        "ranks": [
            ("bronze", "Бронза"),
            ("silver", "Серебро"),
            ("gold", "Золото"),
            ("platinum", "Платина"),
            ("diamond", "Алмаз"),
            ("elite", "Элита"),
            ("champion", "Чемпион"),
            ("unreal", "Анриал"),
        ],
        "roles": [],
    },
    {
        "slug": "minecraft",
        "name": "Minecraft",
        "platforms": ["pc", "console", "mobile"],
        "max_party_size": None,
        "ranks": [],
        "roles": [],
    },
    {
        "slug": "roblox",
        "name": "Roblox",
        "platforms": ["pc", "console", "mobile"],
        "max_party_size": None,
        "ranks": [],
        "roles": [],
    },
]


def seed() -> None:
    with SessionLocal.begin() as session:
        for order, data in enumerate(GAMES):
            game = session.scalar(select(Game).where(Game.slug == data["slug"]))
            if game is None:
                game = Game(slug=data["slug"])
                session.add(game)
            game.name = data["name"]
            game.platforms = data["platforms"]
            game.max_party_size = data["max_party_size"]
            game.sort_order = order

            ranks_by_code = {rank.code: rank for rank in game.ranks}
            for tier, (code, name) in enumerate(data["ranks"], start=1):
                rank = ranks_by_code.get(code)
                if rank is None:
                    rank = GameRank(code=code)
                    game.ranks.append(rank)
                rank.name = name
                rank.tier = tier

            roles_by_code = {role.code: role for role in game.roles}
            for sort_order, (code, name) in enumerate(data["roles"]):
                role = roles_by_code.get(code)
                if role is None:
                    role = GameRole(code=code)
                    game.roles.append(role)
                role.name = name
                role.sort_order = sort_order

    print(f"Игр в справочнике: {len(GAMES)}")


if __name__ == "__main__":
    seed()
