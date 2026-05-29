from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://telegram_crm:telegram_crm@db:5432/telegram_crm"
    frontend_origin: str = "http://localhost:5173"
    telegram_bot_token: str | None = None
    public_webhook_url: str | None = None
    telegram_webhook_secret: str = "change_me_local_secret"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def telegram_webhook_url(self) -> str | None:
        if not self.public_webhook_url:
            return None
        return f"{self.public_webhook_url.rstrip('/')}/telegram/webhook"


@lru_cache
def get_settings() -> Settings:
    return Settings()
