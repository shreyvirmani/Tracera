from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            _BACKEND_DIR / ".env",
            _ROOT_DIR / ".env",
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/Tracera",
        description="PostgreSQL connection URL",
    )
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="Backend host")
    BACKEND_PORT: int = Field(default=8000, description="Backend port")
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )

    # Scanner resource limits. These bound how much time, bandwidth, and
    # redirect-following a single scan may consume.
    SCANNER_TIMEOUT_SECONDS: float = Field(
        default=10.0, description="Per-request timeout for the collector"
    )
    SCANNER_CONNECT_TIMEOUT_SECONDS: float = Field(
        default=5.0, description="Connect timeout for the collector"
    )
    SCANNER_TOTAL_TIME_SECONDS: float = Field(
        default=25.0,
        description="Total wall-clock budget for one scan including all redirects",
    )
    SCANNER_MAX_RESPONSE_BYTES: int = Field(
        default=10 * 1024 * 1024, description="Maximum response body size"
    )
    SCANNER_MAX_REDIRECTS: int = Field(default=5, description="Maximum redirects followed per scan")
    SCANNER_ALLOWED_PORTS: list[int] = Field(
        default=[80, 443, 8080, 8443],
        description="Destination ports the collector may connect to",
    )

    # Rate limiting for scan creation (in-memory, per client IP).
    SCAN_RATE_LIMIT_MAX: int = Field(
        default=10, description="Maximum scan creations per window per client"
    )
    SCAN_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # ML analysis (optional, graceful — never blocks or alters deterministic results)
    ML_ANALYSIS_ENABLED: bool = Field(default=True, description="Enable optional ML analysis")
    ML_ARTIFACT_DIR: str = Field(default="", description="Path to ML artifact directory")

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def db_echo(self) -> bool:
        return self.DB_ECHO

    @property
    def ml_analysis_enabled(self) -> bool:
        return self.ML_ANALYSIS_ENABLED

    @property
    def ml_artifact_dir(self) -> str:
        return self.ML_ARTIFACT_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
