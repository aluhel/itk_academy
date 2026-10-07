import pytest

from itk_academy.config import Settings, get_settings


def test_celery_broker_uses_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/x")
    settings = Settings()
    assert settings.celery_broker_url == "sqla+postgresql+psycopg2://u:p@db:5432/x"


def test_celery_broker_empty_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url == ""
    assert settings.celery_broker_url == ""


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
