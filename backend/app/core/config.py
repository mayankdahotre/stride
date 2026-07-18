from functools import lru_cache
from typing import Annotated, Any
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Stride API"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str = ""
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    cors_allow_credentials: bool = False

    database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "stride_db"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    db_connect_timeout: int = 2

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    model_request_timeout: float = 120.0
    conversational_model_enabled: bool = True
    langgraph_postgres_checkpointer: bool = True

    embeddings_enabled: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_cors(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must list explicit origins; wildcard is not allowed")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{quote_plus(self.postgres_user)}:"
            f"{quote_plus(self.postgres_password)}@{self.postgres_host}:"
            f"{self.postgres_port}/{quote_plus(self.postgres_db)}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()