from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tracera",
        description="PostgreSQL connection URL",
    )
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="Backend host")
    BACKEND_PORT: int = Field(default=8000, description="Backend port")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
