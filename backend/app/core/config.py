import json
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def _parse_origins(value: str | list[str] | None, defaults: list[str]) -> list[str]:
    if value is None:
        return defaults
    if isinstance(value, list):
        if not all(isinstance(origin, str) for origin in value):
            raise ValueError("Origins must be strings")
        return value

    raw_origins = value.strip()
    if not raw_origins:
        return defaults
    if raw_origins.startswith("["):
        try:
            parsed = json.loads(raw_origins)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Origins must be a comma-separated string or a JSON array"
            ) from exc
        if not isinstance(parsed, list) or not all(
            isinstance(origin, str) for origin in parsed
        ):
            raise ValueError("Origins must be a comma-separated string or a JSON array")
        return parsed
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


class Settings(BaseSettings):
    APP_ENV: Literal["development", "test", "production"] = "production"
    DATABASE_URL: str = Field(default="")
    JWT_SECRET_KEY: str = Field(default="",min_length=32)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    ALLOW_PUBLIC_ROLE_REGISTRATION: bool = False
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: _DEFAULT_CORS_ORIGINS.copy()
    )
    ALLOWED_ORIGINS: str | None = None

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: str | list[str]) -> list[str]:
        return _parse_origins(value, _DEFAULT_CORS_ORIGINS)

    @property
    def allowed_origins(self) -> list[str]:
        if self.ALLOWED_ORIGINS is not None:
            return _parse_origins(self.ALLOWED_ORIGINS, self.CORS_ALLOWED_ORIGINS)
        return self.CORS_ALLOWED_ORIGINS

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return self.DATABASE_URL

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "ignore"
    )


#Instantiate a single shared settings instance for the app to  import
settings = Settings()
