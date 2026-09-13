"""
HTTP Archive BigQuery Configuration

Configuration for HTTP Archive BigQuery data extraction.
All settings should be configured here rather than hardcoded in extraction scripts.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from pathlib import Path


@dataclass
class HTTPArchiveConfig:
    """Configuration for HTTP Archive BigQuery data extraction."""
    
    # Source dataset configuration
    project_id: str = "httparchive"  # BigQuery project ID
    dataset_id: str = "summary_pages"  # BigQuery dataset (summary_pages or summary_requests)
    table_prefix: str = "2025_07_01_"  # Table prefix for specific crawl (YYYY_MM_DD_)
    
    # Crawl identification
    crawl_date: str = "2025-07-01"  # Crawl date (YYYY-MM-DD)
    crawl_name: str = "2025 Web Almanac"  # Human-readable name
    
    # Desktop vs Mobile
    client: str = "desktop"  # "desktop" or "mobile"
    
    # Sampling
    sample_size: int = 10000  # Target number of unique origins
    random_seed: int = 42
    
    # BigQuery settings
    max_bytes_billed: int = 10_000_000_000  # 10 GB limit
    query_timeout_seconds: int = 300
    
    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("ml/data/http_archive"))
    raw_dir: Path = field(default_factory=lambda: Path("ml/data/http_archive/raw"))
    processed_dir: Path = field(default_factory=lambda: Path("ml/data/http_archive/processed"))
    reports_dir: Path = field(default_factory=lambda: Path("ml/data/http_archive/reports"))
    
    # Feature extraction settings
    feature_schema_version: str = "v1"
    
    # Minimum records per origin for inclusion
    min_records_per_origin: int = 1
    
    # Status codes to include
    valid_status_codes: List[int] = field(default_factory=lambda: [200])
    
    # Content types to include
    html_content_types: List[str] = field(default_factory=lambda: [
        "text/html",
        "application/xhtml+xml",
    ])
    
    def __post_init__(self):
        """Validate and create directories."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct full table ID
        self.table_id = f"{self.project_id}.{self.dataset_id}.{self.table_prefix}{self.client}"
    
    def get_table_id(self) -> str:
        """Get the full BigQuery table ID."""
        return self.table_id
    
    def to_dict(self) -> dict:
        """Serialize config to dictionary for reporting."""
        return {
            "project_id": self.project_id,
            "dataset_id": self.dataset_id,
            "table_prefix": self.table_prefix,
            "crawl_date": self.crawl_date,
            "crawl_name": self.crawl_name,
            "client": self.client,
            "sample_size": self.sample_size,
            "random_seed": self.random_seed,
            "feature_schema_version": self.feature_schema_version,
            "table_id": self.table_id,
        }


# Default configuration instance
DEFAULT_CONFIG = HTTPArchiveConfig()


# Alternative configurations for different crawls
CRAWL_CONFIGS = {
    "2025_web_almanac_desktop": HTTPArchiveConfig(
        crawl_date="2025-07-01",
        crawl_name="2025 Web Almanac Desktop",
        table_prefix="2025_07_01_",
        client="desktop",
    ),
    "2025_web_almanac_mobile": HTTPArchiveConfig(
        crawl_date="2025-07-01",
        crawl_name="2025 Web Almanac Mobile",
        table_prefix="2025_07_01_",
        client="mobile",
    ),
    "2024_web_almanac_desktop": HTTPArchiveConfig(
        crawl_date="2024-07-01",
        crawl_name="2024 Web Almanac Desktop",
        table_prefix="2024_07_01_",
        client="desktop",
    ),
    "2024_web_almanac_mobile": HTTPArchiveConfig(
        crawl_date="2024-07-01",
        crawl_name="2024 Web Almanac Mobile",
        table_prefix="2024_07_01_",
        client="mobile",
    ),
}


def get_config(crawl_key: str = "2025_web_almanac_desktop") -> HTTPArchiveConfig:
    """Get configuration for a specific crawl."""
    return CRAWL_CONFIGS.get(crawl_key, DEFAULT_CONFIG)