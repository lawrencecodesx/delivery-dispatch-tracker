import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_normalizes_render_postgres_scheme():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        JWT_SECRET_KEY="x" * 32,
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://user:pass@host:5432/db"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://app.vercel.app", ["https://app.vercel.app"]),
        (
            "https://app.vercel.app, http://localhost:5173",
            ["https://app.vercel.app", "http://localhost:5173"],
        ),
        (
            '["https://app.vercel.app","http://localhost:5173"]',
            ["https://app.vercel.app", "http://localhost:5173"],
        ),
        ("*", ["*"]),
    ],
)
def test_allowed_origins_supports_plain_and_json_values(value, expected):
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        JWT_SECRET_KEY="x" * 32,
        ALLOWED_ORIGINS=value,
    )

    assert settings.allowed_origins == expected


def test_cors_allowed_origins_environment_accepts_comma_separated_value(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.vercel.app,*")
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        JWT_SECRET_KEY="x" * 32,
    )

    assert settings.CORS_ALLOWED_ORIGINS == ["https://app.vercel.app", "*"]


def test_cors_allowed_origins_environment_accepts_json_array(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["https://app.vercel.app","http://localhost:5173"]',
    )
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        JWT_SECRET_KEY="x" * 32,
    )

    assert settings.CORS_ALLOWED_ORIGINS == [
        "https://app.vercel.app",
        "http://localhost:5173",
    ]


def test_invalid_json_origins_raise_a_clear_validation_error():
    with pytest.raises(ValidationError, match="comma-separated string or a JSON array"):
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql://user:pass@host:5432/db",
            JWT_SECRET_KEY="x" * 32,
            CORS_ALLOWED_ORIGINS="[not-json",
        )
