"""Tests for application configuration."""

import pytest
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(tmp_path):
    """Create temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
APP_NAME=Test App
API_PORT=9000
DATABASE_PATH=./test.db
LOG_LEVEL=DEBUG
METADATA_FORMATS=iso19139,json,schema_org
"""
    )
    
    # Change to temp directory
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_cwd)


def test_settings_singleton():
    """Test that settings is a singleton."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_settings_defaults():
    """Test default settings values."""
    settings = get_settings()
    
    assert settings.app_name == "CEH Dataset Discovery"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.log_level == "INFO"


def test_settings_database_path():
    """Test database path configuration."""
    settings = get_settings()
    
    assert settings.database_path == "./data/datasets.db"
    assert isinstance(settings.database_dir, Path)


def test_settings_directories_creation():
    """Test that ensure_directories creates required paths."""
    with TemporaryDirectory() as tmpdir:
        settings = Settings(
            _env_file=None,  # Don't load from .env
            database_path=f"{tmpdir}/test.db",
            chroma_path=f"{tmpdir}/chroma",
            supporting_docs_cache_dir=f"{tmpdir}/docs",
            log_file=f"{tmpdir}/logs/app.log",
            metadata_formats=["iso19139", "json"]
        )
        
        settings.ensure_directories()
        
        assert settings.database_dir.exists()
        assert settings.chroma_dir.exists()
        assert settings.supporting_docs_dir.exists()
        assert settings.logs_dir.exists()


def test_settings_ceh_api_configuration():
    """Test CEH API configuration."""
    settings = get_settings()
    
    assert "catalogue.ceh.ac.uk" in settings.ceh_api_base_url
    assert settings.ceh_api_timeout == 30
    assert settings.ceh_api_max_retries == 3


def test_settings_batch_processing_config():
    """Test batch processing configuration."""
    settings = get_settings()
    
    assert settings.batch_size == 10
    assert settings.max_concurrent_downloads == 5


def test_metadata_formats_parsing():
    """Test that metadata_formats parses correctly from string."""
    settings = Settings(
        _env_file=None,
        metadata_formats="iso19139,json,schema_org"
    )
    
    assert settings.metadata_formats == ["iso19139", "json", "schema_org"]


def test_metadata_formats_list():
    """Test that metadata_formats works with list input."""
    settings = Settings(
        _env_file=None,
        metadata_formats=["iso19139", "json"]
    )
    
    assert settings.metadata_formats == ["iso19139", "json"]


def test_metadata_formats_with_whitespace():
    """Test that metadata_formats strips whitespace."""
    settings = Settings(
        _env_file=None,
        metadata_formats="iso19139 , json , schema_org"
    )
    
    assert settings.metadata_formats == ["iso19139", "json", "schema_org"]