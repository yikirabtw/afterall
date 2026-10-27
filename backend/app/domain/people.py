"""Лента людей: правила показа и «Совпадение N%» — насколько человек подходит и почему."""

from dataclasses import dataclass
from datetime import timedelta

from app.db.enums import LookingFor, PlayStyle

# Пропущенные анкеты снова появятся через 3 дня: людей в бете немного, лента не должна пустеть навсегда
SKIP_COOLDOWN = timedelta(days=3)
# Сколько недавно активных людей берём из базы, чтобы отсортировать их по совпадению
CANDIDATE_POOL = 200
MAX_REASONS = 3

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


@dataclass
class Compatibility:
    score: int  # 0–100
    common_game_ids: list[int]
    reasons: list[str]  # короткие фразы «почему вам по пути», самые важные первыми


def compatibility(me: Traits, other: Traits, game_names: dict[int, str]) -> Compatibility:
    """Баллы: общие игры 35 и +5 за каждую следующую (до 40), общая основная 10, близкий ранг 10,
    стиль 15, цели 10, язык 5, микрофон 10. Идеальная пара по одной игре — 95%, по двум — 100%.
    """
    score = 0
    reasons: list[str] = []

    common = [game_id for game_id in other.games if game_id in me.games]
    if common:
        score += min(35 + 5 * (len(common) - 1), 40)
        reasons.append("Оба играете в " + " и ".join(game_names.get(game_id, "игру") for game_id in common[:2]))
        if me.main_game_id is not None and me.main_game_id == other.main_game_id:
            score += 10

    for game_id in common:
        mine, theirs = me.games[game_id], other.games[game_id]
        if mine is not None and theirs is not None and abs(mine - theirs) <= 1:
            score += 10
            reasons.append(f"Близкий ранг в {game_names.get(game_id, 'игре')}")
            break

    style_gap = abs(_STYLE_ORDER.index(me.play_style) - _STYLE_ORDER.index(other.play_style))
    if style_gap == 0:
        score += 15
        reasons.append(f"Один стиль — {STYLE_NAMES[me.play_style]}")
    elif style_gap == 1:
        score += 7

    if me.looking_for == other.looking_for:
        score += 10
        reasons.append("Ищете одно и то же")
    elif LookingFor.BOTH in (me.looking_for, other.looking_for):
        score += 7

    if me.languages & other.languages:
        score += 5

    if me.has_mic and other.has_mic:
        score += 10
        reasons.append("У обоих есть микрофон")

    return Compatibility(score=min(score, 100), common_game_ids=common, reasons=reasons[:MAX_REASONS])
