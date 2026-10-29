"""Все тексты бота в одном месте — чтобы править их, не трогая логику. Разметка — HTML."""

from html import escape


def welcome_new(name: str) -> str:
    return (
        f"Привет, {escape(name)}! 👋\n\n"
        "Здесь можно найти тиммейтов для игр или компанию на вечер.\n\n"
        "<b>Как это работает</b>\n"
        "1. Заполняешь анкету: игры, ранг, когда обычно играешь.\n"
        "2. Создаёшь пати или откликаешься на чужие.\n"
        "3. Когда тебя приняли — видишь контакты и идёте играть."
    )


def welcome_back(name: str) -> str:
    return f"С возвращением, {escape(name)}! Кого ищем сегодня? 🎮"


OPEN_APP_HINT = "Жми кнопку ниже 👇"

APP_NOT_READY = "Приложение пока в разработке — скоро здесь можно будет искать пати."

HELP = (
    "<b>Что умеет бот</b>\n"
    "Помогает собрать пати в игру или компанию на вечер.\n\n"
    "<b>Команды</b>\n"
    "/start — главное меню\n"
    "/help — эта справка\n\n"
    "<b>Безопасность</b>\n"
    "• Контакты видны только тем, кого приняли в пати.\n"
    "• Точное местоположение мы не спрашиваем и не показываем.\n"
    "• На любого пользователя можно пожаловаться или заблокировать его."
)

FALLBACK = "Я пока понимаю только команды. Нажми /help."

BANNED = "Твой аккаунт заблокирован. Если считаешь, что это ошибка, обратись в поддержку."

# Кнопки
BUTTON_OPEN_APP = "🎮 Открыть приложение"
BUTTON_HELP = "❓ Как это работает"
MENU_BUTTON = "Открыть"

# Подсказки к командам в меню Telegram
COMMAND_START = "Главное меню"
COMMAND_HELP = "Справка"


# --- Уведомления (шлёт API, см. app/services/notify.py) ---
PREVIEW_MAX = 120  # сколько текста сообщения показываем в уведомлении


def _preview(text: str) -> str:
    text = " ".join(text.split())
    return escape(text if len(text) <= PREVIEW_MAX else text[: PREVIEW_MAX - 1] + "…")


def notify_match(name: str) -> str:
    return f"💘 <b>Взаимный лайк!</b>\nУ тебя мэтч с {escape(name)}. Напиши первым?"


def notify_direct_message(sender: str, text: str) -> str:
    return f"💬 <b>{escape(sender)}</b>\n{_preview(text)}"


def notify_lobby_message(sender: str, lobby_title: str, text: str) -> str:
    return f"💬 <b>{escape(sender)}</b> в пати «{escape(lobby_title)}»\n{_preview(text)}"


def notify_application(name: str, lobby_title: str, note: str | None) -> str:
    text = f"🙋 <b>{escape(name)}</b> хочет в твою пати «{escape(lobby_title)}»"
    return f"{text}\n«{_preview(note)}»" if note else text


def notify_accepted(lobby_title: str) -> str:
    return f"✅ Тебя приняли в пати «{escape(lobby_title)}». Заходи в чат пати — договоритесь, когда начинаете."


def notify_declined(lobby_title: str) -> str:
    return f"В пати «{escape(lobby_title)}» тебя не взяли. Загляни в ленту — там есть и другие пати."


BUTTON_WRITE = "💬 Написать"
BUTTON_REPLY = "💬 Ответить"
BUTTON_OPEN_CHAT = "💬 Открыть чат"
BUTTON_OPEN_LOBBY = "🎮 Открыть пати"
BUTTON_PARTY_CHAT = "💬 Чат пати"
BUTTON_FEED = "🎮 Лента пати"


# --- Жалобы — модераторам (см. app/bot/handlers/moderation.py) ---

REPORT_REASONS = {
    "minor_safety": "🚨 Угроза безопасности подростка",
    "toxic": "Оскорбления или травля",
    "spam": "Спам или реклама",
    "scam": "Мошенничество",
    "inappropriate": "Неприличные фото или сообщения",
    "fake_profile": "Фейковая анкета, чужие фото",
    "other": "Другое",
}


def report_card(
    report_id: int,
    reason: str,
    target: str,
    reporter: str,
    comment: str | None,
    messages: list[tuple[str, str]],
) -> str:
    """target и reporter — уже готовые подписи: имя, ник, возраст, id (собирает person_label)."""
    lines = [
        f"<b>Жалоба #{report_id}</b> · {REPORT_REASONS.get(reason, escape(reason))}",
        f"На: {target}",
        f"От: {reporter}",
    ]
    if comment:
        lines.append(f"Комментарий: {_preview(comment)}")
    if messages:
        lines.append("\n<b>Последние сообщения</b>")
        lines.extend(f"<b>{escape(author)}:</b> {_preview(text)}" for author, text in messages)
    return "\n".join(lines)


def person_label(name: str, username: str | None, age: int | None, user_id: int) -> str:
    nick = f" @{escape(username)}" if username else ""
    years = f", {age}" if age is not None else ""
    return f"{escape(name)}{years}{nick} (id {user_id})"


MOD_BAN_WEEK = "⛔ Бан на 7 дней"
MOD_BAN_FOREVER = "⛔ Навсегда"
MOD_REJECT = "✖ Отклонить"
MOD_NO_RIGHTS = "Разбирать жалобы могут только модераторы."
MOD_ALREADY_DONE = "По этой жалобе уже есть решение."


def mod_decision(action: str, moderator: str) -> str:
    labels = {"ban7": "бан на 7 дней", "ban": "бан навсегда", "reject": "жалоба отклонена"}
    return f"\n\n<b>Решение:</b> {labels[action]} — {escape(moderator)}"


# --- Тарифы: выдача админом (см. app/bot/handlers/admin.py) ---

PLAN_NAMES = {"plus": "Plus", "premium": "Premium"}

ADMIN_PLAN_HELP = (
    "<b>Выдать подписку</b>\n"
    "/premium — себе на 30 дней\n"
    "/premium 7 — себе на 7 дней\n"
    "/premium @ник 30 — человеку по нику в Telegram\n"
    "/premium 123456789 30 — по Telegram ID\n"
    "/plus … — то же для Plus\n"
    "/free @ник — снять подписку"
)
ADMIN_USER_NOT_FOUND = "Такого пользователя нет в базе — пусть сначала откроет бота."


def _date(value) -> str:
    return value.strftime("%d.%m.%Y")


def plan_granted(name: str, plan: str, until) -> str:
    return f"Готово: <b>{PLAN_NAMES[plan]}</b> у {escape(name)} до {_date(until)}."


def plan_revoked(name: str, count: int) -> str:
    return f"Готово: подписки {escape(name)} закончились." if count else f"У {escape(name)} нет действующей подписки."


def plan_gift(plan: str, until) -> str:
    return f"🎁 Тебе выдан <b>{PLAN_NAMES[plan]}</b> до {_date(until)}. Загляни в магазин в приложении."


# --- Приглашение в закрытую пати (ссылка t.me/<бот>?start=join_<код>) ---


def invite_open(lobby_title: str) -> str:
    return f"🔒 Тебя зовут в закрытую пати «{escape(lobby_title)}». Открой и откликнись 👇"


INVITE_EXPIRED = "Приглашение устарело — пати уже нет. Попроси новую ссылку."

