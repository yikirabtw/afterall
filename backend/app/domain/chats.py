from datetime import timedelta

MESSAGE_MAX = 1000  # символов в сообщении
PAGE_SIZE = 50  # сообщений за один запрос
RATE_WINDOW = timedelta(minutes=1)
RATE_LIMIT = 30  # сообщений в минуту от одного человека — живому хватит, спам-боту нет
LOBBY_CHAT_KEEP = timedelta(days=7)  # чат закончившейся пати ещё неделю виден в списке (только чтение)
PREVIEW_MAX = 120  # длина превью последнего сообщения в списке чатов
# Человек заходил в приложение недавно — он в нём (список чатов опрашивается раз в 15 с), уведомление не нужно
NOTIFY_IF_AWAY = timedelta(seconds=45)
