from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: str = "LMS"
    env: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    events_provider_url: str = "http://events-provider.dev-2.python-labs.ru"
    events_provider_api_key: str = ""

    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
