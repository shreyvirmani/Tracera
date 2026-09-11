from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import ipaddress


class Settings(BaseSettings):
    app_name: str = "Tracera"
    environment: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/tracera")

    collector_timeout_seconds: float = 10.0
    collector_max_response_size: int = 2_000_000
    collector_max_redirects: int = 5
    collector_user_agent: str = "Tracera/1.0 (+https://tracera.dev)"

    ssrf_block_private: bool = True
    ssrf_block_loopback: bool = True
    ssrf_block_link_local: bool = True
    ssrf_block_multicast: bool = True
    ssrf_allowed_schemes: List[str] = ["http", "https"]

    rate_limit_requests_per_minute: int = 30

    feature_schema_version: str = "v1"

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


settings = Settings()