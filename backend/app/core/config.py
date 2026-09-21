from functools import lru_cache
from typing import List

import ipaddress
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Tracera"
    environment: str = "development"
    log_level: str = "INFO"

    backend_host: str = Field(default="0.0.0.0", description="Backend host")
    backend_port: int = Field(default=8000, description="Backend port")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tracera",
        description="PostgreSQL connection URL",
    )
    db_echo: bool = Field(default=False, description="Echo SQL queries")

    collector_timeout_seconds: float = Field(
        default=10.0, description="Collector timeout in seconds"
    )
    collector_max_response_size: int = Field(
        default=2_000_000, description="Max response size in bytes"
    )
    collector_max_redirects: int = Field(default=5, description="Max redirects")
    collector_user_agent: str = Field(
        default="Tracera/1.0 (+https://tracera.dev)", description="Collector user agent"
    )

    ssrf_block_private: bool = Field(default=True, description="Block private IPs")
    ssrf_block_loopback: bool = Field(default=True, description="Block loopback IPs")
    ssrf_block_link_local: bool = Field(default=True, description="Block link-local IPs")
    ssrf_block_multicast: bool = Field(default=True, description="Block multicast IPs")
    ssrf_allowed_schemes: List[str] = Field(
        default=["http", "https"], description="Allowed URL schemes"
    )

    rate_limit_requests_per_minute: int = Field(
        default=30, description="Rate limit requests per minute"
    )

    feature_schema_version: str = Field(default="features-v1", description="Feature schema version")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("ff00::/8"),
]


def is_private_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_RANGES)
    except ValueError:
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()