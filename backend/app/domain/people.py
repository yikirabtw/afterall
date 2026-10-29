"""Лента людей: правила показа и «Совпадение N%» — насколько человек подходит и почему."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from app.db.enums import LookingFor, PlayStyle

# Пропущенные анкеты снова появятся через 3 дня: людей в бете немного, лента не должна пустеть навсегда
SKIP_COOLDOWN = timedelta(days=3)
# Сколько недавно активных людей берём из базы, чтобы отсортировать их по совпадению
CANDIDATE_POOL = 200
MAX_REASONS = 3
# Разница FACEIT ELO, при которой ранг считается близким (примерно один уровень FACEIT)
FACEIT_CLOSE_ELO = 200

STYLE_NAMES = {PlayStyle.CHILL: "чилл", PlayStyle.BALANCED: "баланс", PlayStyle.TRYHARD: "трайхард"}
_STYLE_ORDER = [PlayStyle.CHILL, PlayStyle.BALANCED, PlayStyle.TRYHARD]


@dataclass
class Traits:
    """Всё, что важно для совпадения. Ранг — числом (tier), чтобы сравнивать «близко или нет»."""

    games: dict[int, int | None]  # game_id → tier ранга, None — ранг не указан
    main_game_id: int | None
    play_style: PlayStyle
    looking_for: LookingFor
    languages: set[str]
    has_mic: bool
    faceit: dict[int, int] = field(default_factory=dict)  # game_id → FACEIT ELO, если указан


@dataclass
class Compatibility:
    score: int  # 0–100
    common_game_ids: list[int]
    reasons: list[str]  # короткие фразы «почему вам по пути», самые важные первыми


# Лента «Кого ищу» (решение пользователя): режим задаёт, кого показывать и что важнее в «Совпадении».
# None — «Все»: прежняя формула. Веса каждого режима в сумме дают 100.
FeedMode = Literal["play", "chat", "friends"]

WEIGHTS: dict[FeedMode | None, dict[str, int]] = {
    None: {"games": 35, "games_extra": 5, "games_max": 40, "main": 10, "rank": 10, "style": 15, "looking": 10,
           "language": 5, "mic": 10},
    # Побегать: общая игра, близкий ранг, микрофон
    "play": {"games": 35, "games_extra": 5, "games_max": 40, "main": 10, "rank": 20, "style": 15, "looking": 0,
             "language": 0, "mic": 15},
    # Поболтать: характер и язык важнее рангов, общая игра — просто тема для разговора
    "chat": {"games": 20, "games_extra": 0, "games_max": 20, "main": 0, "rank": 0, "style": 25, "looking": 20,
             "language": 20, "mic": 15},
    # Друзья надолго: совпадают цели и стиль
    "friends": {"games": 20, "games_extra": 0, "games_max": 20, "main": 0, "rank": 0, "style": 25, "looking": 25,
                "language": 20, "mic": 10},
}
STYLE_NEAR = 7 / 15  # соседний стиль — почти половина баллов за стиль
LOOKING_BOTH = 0.7  # один ищет «и то, и то» — большая часть баллов за цели


def compatibility(me: Traits, other: Traits, game_names: dict[int, str], mode: FeedMode | None = None) -> Compatibility:
    """«Совпадение» в процентах и причины. Без режима: общие игры 35 и +5 за каждую следующую (до 40),
    общая основная 10, близкий ранг 10, стиль 15, цели 10, язык 5, микрофон 10 — идеальная пара по одной игре 95%,
    по двум — 100%. В режимах «Кого ищу» — свои веса (WEIGHTS), причины — по важности.
    """
    w = WEIGHTS[mode]
    score = 0
    reasons: list[tuple[int, str]] = []

    common = [game_id for game_id in other.games if game_id in me.games]
    if common:
        points = min(w["games"] + w["games_extra"] * (len(common) - 1), w["games_max"])
        score += points
        reasons.append((points, "Оба играете в " + " и ".join(game_names.get(game_id, "игру") for game_id in common[:2])))
        if me.main_game_id is not None and me.main_game_id == other.main_game_id:
            score += w["main"]

    # Близкий ранг: соседние ранги или, если у обоих указан FACEIT, разница ELO до FACEIT_CLOSE_ELO
    if w["rank"]:
        for game_id in common:
            mine, theirs = me.games[game_id], other.games[game_id]
            my_elo, their_elo = me.faceit.get(game_id), other.faceit.get(game_id)
            if my_elo is not None and their_elo is not None and abs(my_elo - their_elo) <= FACEIT_CLOSE_ELO:
                score += w["rank"]
                reasons.append((w["rank"], f"Близкий FACEIT в {game_names.get(game_id, 'игре')}"))
                break
            if mine is not None and theirs is not None and abs(mine - theirs) <= 1:
                score += w["rank"]
                reasons.append((w["rank"], f"Близкий ранг в {game_names.get(game_id, 'игре')}"))
                break

    style_gap = abs(_STYLE_ORDER.index(me.play_style) - _STYLE_ORDER.index(other.play_style))
    if style_gap == 0:
        score += w["style"]
        reasons.append((w["style"], f"Один стиль — {STYLE_NAMES[me.play_style]}"))
    elif style_gap == 1:
        score += round(w["style"] * STYLE_NEAR)

    if w["looking"]:
        if me.looking_for == other.looking_for:
            score += w["looking"]
            reasons.append((w["looking"], "Ищете одно и то же"))
        elif LookingFor.BOTH in (me.looking_for, other.looking_for):
            score += round(w["looking"] * LOOKING_BOTH)

    if me.languages & other.languages:
        score += w["language"]

    if w["mic"] and me.has_mic and other.has_mic:
        score += w["mic"]
        reasons.append((w["mic"], "У обоих есть микрофон"))

    if mode is not None:
        reasons.sort(key=lambda reason: reason[0], reverse=True)  # в режимах — сначала самое важное для него
    return Compatibility(
        score=min(score, 100), common_game_ids=common, reasons=[text for _, text in reasons[:MAX_REASONS]]
    )
