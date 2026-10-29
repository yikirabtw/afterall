"""Настройки из переменных окружения: то, что вводят руками в панели хостинга, не должно ронять сервер."""

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("921506676", [921506676]), ("[921506676]", [921506676]), ("1, 2", [1, 2]), ("[1,2]", [1, 2]), ("", [])],
)
def test_admin_ids_accept_any_spelling(monkeypatch, raw, expected):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", raw)
    assert Settings(_env_file=None).admin_telegram_ids == expected
