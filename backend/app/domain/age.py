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
