from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Локально — SQLite-файл, в продакшене — PostgreSQL (см. .env.example)
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'dev.db').as_posix()}"

    # Токен от @BotFather. Без него бот не запустится, остальное работает.
    bot_token: SecretStr | None = None
    # HTTPS-адрес мини-приложения. Пока его нет — кнопка «Открыть приложение» не показывается.
    webapp_url: str | None = None

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # Откуда ещё (кроме WEBAPP_URL) браузер может обращаться к API; по умолчанию — dev-сервер Vite
    cors_origins: list[str] = ["http://localhost:5173"]
    # Сколько действует подпись initData. Дольше — мини-приложение нужно открыть заново.
    init_data_max_age_hours: int = 24

    # --- Хостинг ---
    # Публичный HTTPS-адрес сервиса. На Render подставляется сам (RENDER_EXTERNAL_URL).
    # Если задан — бот работает через вебхук внутри API, а не отдельным процессом.
    public_url: str | None = Field(default=None, validation_alias=AliasChoices("PUBLIC_URL", "RENDER_EXTERNAL_URL"))
    # Секрет, которым Telegram подписывает запросы на вебхук. Не задан — выводится из токена бота.
    webhook_secret: SecretStr | None = None
    # Собранное мини-приложение (webapp/dist). Если папка есть — API отдаёт его по адресу /
    static_dir: Path | None = None

    # Telegram ID админов (JSON-список, например [123456789]): им приходят жалобы с кнопками бана,
    # даже если в базе у них нет роли admin. Задаётся в панели хостинга.
    admin_telegram_ids: list[int] = []


settings = Settings()
