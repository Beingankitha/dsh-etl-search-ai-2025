"""
Application configuration using Pydantic Settings.
Loads values from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "CEH Dataset Discovery"
    app_env: str = "development"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database Configuration (Issue #5)
    database_path: str = "./data/datasets.db"
    database_echo: bool = False  # Set to True for SQL query logging

    # CEH API Configuration (Issue #4)
    ceh_api_base_url: str = "https://catalogue.ceh.ac.uk"
    ceh_api_timeout: int = 30
    ceh_api_max_retries: int = 3
    ceh_api_retry_delay: int = 1

    # HTTP Client Configuration
    http_timeout: int = 30
    http_max_retries: int = 3
    http_retry_backoff_factor: float = 0.5

    # Supporting Documents Configuration (Issue #4)
    supporting_docs_cache_dir: str = "./data/supporting_docs"
    supporting_docs_max_file_size: int = 104857600  # 100MB
    web_folder_max_depth: int = 3

    # Vector Store (Issue #7)
    chroma_path: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Ollama LLM Configuration (Issue #7)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout: int = 120

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # Metadata Extraction (Issue #4)
    metadata_formats: List[str] = ["iso19139", "json", "schema_org", "rdf"]
    extract_text_from_pdfs: bool = True
    extract_text_from_docx: bool = True

    # Batch Processing (Issue #6)
    batch_size: int = 10
    max_concurrent_downloads: int = 5

    # Field Validators
    @field_validator("metadata_formats", mode="before")
    @classmethod
    def parse_metadata_formats(cls, v):
        """Parse metadata_formats from comma-separated string or list."""
        if isinstance(v, str):
            # Split comma-separated string and strip whitespace
            return [fmt.strip() for fmt in v.split(",")]
        elif isinstance(v, list):
            return v
        return v

    # Paths as Properties (for convenience)
    @property
    def database_dir(self) -> Path:
        """Get database directory."""
        return Path(self.database_path).parent

    @property
    def supporting_docs_dir(self) -> Path:
        """Get supporting documents cache directory."""
        return Path(self.supporting_docs_cache_dir)

    @property
    def chroma_dir(self) -> Path:
        """Get Chroma vector store directory."""
        return Path(self.chroma_path)

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        return Path(self.log_file).parent

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.database_dir.mkdir(parents=True, exist_ok=True)
        self.supporting_docs_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings singleton."""
    settings = Settings()
    settings.ensure_directories()
    return settings