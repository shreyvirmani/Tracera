"""
Tests for HTTP Archive BigQuery data pipeline.
"""

import pytest
import pandas as pd
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.data.http_archive.config import HTTPArchiveConfig, DEFAULT_CONFIG, get_config


class TestHTTPArchiveConfig:
    """Test HTTPArchiveConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HTTPArchiveConfig()
        assert config.project_id == "httparchive"
        assert config.dataset_id == "summary_pages"
        assert config.client == "desktop"
        assert config.feature_schema_version == "v1"
        assert config.random_seed == 42
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = HTTPArchiveConfig(
            project_id="my-project",
            dataset_id="custom_dataset",
            client="mobile",
            crawl_date="2024-01-01",
        )
        assert config.project_id == "my-project"
        assert config.dataset_id == "custom_dataset"
        assert config.client == "mobile"
        assert config.crawl_date == "2024-01-01"
    
    def test_table_id_generation(self):
        """Test table ID generation."""
        config = HTTPArchiveConfig(
            table_prefix="2025_07_01_",
            client="desktop",
        )
        assert config.table_id == "httparchive.summary_pages.2025_07_01_desktop"
    
    def test_get_table_id(self):
        """Test get_table_id method."""
        config = HTTPArchiveConfig()
        assert config.get_table_id() == "httparchive.summary_pages.2025_07_01_desktop"
    
    def test_to_dict(self):
        """Test to_dict serialization."""
        config = HTTPArchiveConfig(crawl_date="2025-01-01")
        d = config.to_dict()
        assert d["crawl_date"] == "2025-01-01"
        assert d["feature_schema_version"] == "v1"
        assert "table_id" in d


class TestConfigPresets:
    """Test predefined configuration presets."""
    
    def test_2025_web_almanac_desktop(self):
        config = get_config("2025_web_almanac_desktop")
        assert config.crawl_date == "2025-07-01"
        assert config.client == "desktop"
        assert config.crawl_name == "2025 Web Almanac Desktop"
    
    def test_2025_web_almanac_mobile(self):
        config = get_config("2025_web_almanac_mobile")
        assert config.crawl_date == "2025-07-01"
        assert config.client == "mobile"
        assert config.crawl_name == "2025 Web Almanac Mobile"
    
    def test_2024_web_almanac_desktop(self):
        config = get_config("2024_web_almanac_desktop")
        assert config.crawl_date == "2024-07-01"
        assert config.client == "desktop"
        assert config.crawl_name == "2024 Web Almanac Desktop"
    
    def test_invalid_config_key(self):
        """Test that invalid config key returns default."""
        config = get_config("invalid_key")
        assert config == DEFAULT_CONFIG


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_post_init_creates_dirs(self, tmp_path):
        """Test that __post_init__ creates output directories."""
        output_dir = tmp_path / "test_output"
        config = HTTPArchiveConfig(output_dir=str(output_dir))
        assert config.raw_dir.exists()
        assert config.processed_dir.exists()
        assert config.reports_dir.exists()
    
    def test_to_dict(self):
        """Test to_dict method includes all relevant fields."""
        config = HTTPArchiveConfig(crawl_date="2025-01-01")
        d = config.to_dict()
        assert d["crawl_date"] == "2025-01-01"
        assert d["feature_schema_version"] == "v1"
        assert "table_id" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])