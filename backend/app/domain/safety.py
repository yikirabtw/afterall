"""Жалобы и блокировки: лимиты и сроки."""

from datetime import timedelta

REPORTS_PER_DAY = 10  # жалоб от одного человека за сутки — честному хватит, травле жалобами нет
REPORTS_WINDOW = timedelta(days=1)
REPORT_CONTEXT_MESSAGES = 10  # сколько последних сообщений переписки видит модератор
BAN_WEEK = timedelta(days=7)
