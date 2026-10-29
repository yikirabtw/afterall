from datetime import date

from app.db.enums import AgeGroup

# Минимальный возраст ещё не утверждён окончательно — меняется здесь
MIN_AGE = 13


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def age_group_for(birth_date: date, today: date | None = None) -> AgeGroup | None:
    """Возрастная группа или None, если человек младше MIN_AGE.

    Группа меняется с днём рождения, поэтому её нужно периодически пересчитывать
    (фоновая задача появится вместе с бэкендом).
    """
    age = age_on(birth_date, today or date.today())
    if age < MIN_AGE:
        return None
    if age <= 15:
        return AgeGroup.TEEN_13_15
    if age <= 17:
        return AgeGroup.TEEN_16_17
    return AgeGroup.ADULT


# --- С кем можно встретиться в ленте людей ---
# Решение пользователя: возраст поиска выбирают сами («от и до»), но поверх — жёсткие рамки, которые не отключаются:
# если хоть один младше 18 — разница не больше 4 лет; совершеннолетние и младше 16 не видят друг друга никогда.
# Правило симметричное, а выбор «от и до» — взаимный: видно, только если каждый попадает в диапазон другого.

ADULT_AGE = 18
SAFE_FROM_ADULTS = 16  # младше этого возраста взрослые не видны и не видят
MINOR_MAX_GAP = 4


def search_limits(age: int) -> tuple[int, int | None]:
    """Рамки возраста поиска: от и до (None — без верхней границы, только у взрослых)."""
    lowest = max(MIN_AGE, age - MINOR_MAX_GAP)
    if age < SAFE_FROM_ADULTS:
        return lowest, min(ADULT_AGE - 1, age + MINOR_MAX_GAP)
    if age < ADULT_AGE:
        return lowest, age + MINOR_MAX_GAP
    # Взрослому несовершеннолетние доступны только 16–17 и только в пределах 4 лет; взрослые — любые
    return min(ADULT_AGE, max(SAFE_FROM_ADULTS, lowest)), None


def can_meet(age: int, other_age: int) -> bool:
    low, high = search_limits(age)
    return other_age >= low and (high is None or other_age <= high)


def _clip(age: int, wanted_min: int | None, wanted_max: int | None) -> tuple[int, int | None]:
    low, high = search_limits(age)
    start = low if wanted_min is None else max(low, wanted_min)
    if wanted_max is None:
        end = high
    else:
        end = wanted_max if high is None else min(high, wanted_max)
    return start, end


def search_range_fits(age: int, wanted_min: int | None, wanted_max: int | None) -> bool:
    """Выбранный диапазон хоть как-то попадает в рамки (после дня рождения рамки сдвигаются и он мог устареть)."""
    start, end = _clip(age, wanted_min, wanted_max)
    return end is None or start <= end


def search_range(age: int, wanted_min: int | None, wanted_max: int | None) -> tuple[int, int | None]:
    """Выбранный диапазон, обрезанный рамками. Устарел целиком — рамки целиком."""
    if not search_range_fits(age, wanted_min, wanted_max):
        return search_limits(age)
    return _clip(age, wanted_min, wanted_max)


def years_ago(today: date, years: int) -> date:
    """Та же дата N лет назад; 29 февраля в невисокосный год — 28-е (как и в age_on)."""
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)
