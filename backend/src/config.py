"""
Application configuration using Pydantic Settings.
Loads values from environment variables and .env file.
"""

import os
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
        extra="ignore", # Ignore unknown environment variables
    )

    # Application
    app_name: str = "CEH Dataset Discovery"
    app_env: str = "development"
    environment: str = "development"  # Alias for app_env
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    server_host: str = "0.0.0.0"  # Alias for api_host
    server_port: int = 8000  # Alias for api_port

    # Database Configuration (Issue #5)
    database_path: str = "./data/datasets.db"
    database_echo: bool = False  # Set to True for SQL query logging

    # CEH API Configuration (Issue #4)
    ceh_api_base_url: str = "https://catalogue.ceh.ac.uk"
    ceh_api_timeout: int = 600  # Increased to 600s (10 min) for large data file downloads & server delays
    ceh_api_max_retries: int = 5  # Increased from 3 to 5 for better resilience
    ceh_api_retry_delay: int = 2  # Increased from 1 to 2 for server recovery time

    # HTTP Client Configuration
    http_timeout: int = 600  # Increased to 600s (10 min) for large data file downloads & server delays
    http_max_retries: int = 5  # Increased from 3 to 5 for better resilience
    http_retry_backoff_factor: float = 0.5

    # Supporting Documents Configuration (Issue #4)
    supporting_docs_cache_dir: str = "./data/supporting_docs"
    supporting_docs_max_file_size: int = 104857600  # 100MB
    web_folder_max_depth: int = 3

    # Vector Store & Embeddings Configuration (Issue #7)
    chroma_path: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"  # Fast model, good accuracy. Alternative: "all-MiniLM-L12-v2" (faster) or "sentence-transformers/all-MiniLM-L6-v2" (same)
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"  # 'cpu' or 'cuda' for GPU
    embedding_normalize: bool = True  # Normalize embeddings for faster similarity
    text_chunk_size: int = 1000  # Characters per chunk for RAG
    text_chunk_overlap: int = 200  # Overlap between chunks

    # Ollama LLM Configuration (Issue #7)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"  # Changed from llama3.2 to match downloaded model to mistral
    ollama_timeout: int = 120

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # Distributed Tracing Configuration (Observability)
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    jaeger_enabled: bool = False  # Disabled by default - enable only if OTLP collector running
    jaeger_service_name: str = "dsh-etl-search-ai"
    jaeger_environment: str = "development"
    jaeger_sample_rate: float = 0.1  # 0.1 = 10% sampling (reduce for production)

    # Metadata Extraction (Issue #4)
    metadata_formats: List[str] = ["iso19139", "json", "schema_org", "rdf"]
    extract_text_from_pdfs: bool = True
    extract_text_from_docx: bool = True

    # Batch Processing (Issue #6)
    batch_size: int = 10
    max_concurrent_downloads: int = 5
    
    # ETL Configuration (Issue #6)
    metadata_identifiers_file: str = "metadata-file-identifiers.txt"
    etl_timeout: int = 300
    etl_batch_size: int = 10

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

    def get(self, key: str, default=None):
        """Get configuration value by key (dict-like interface).
        
        Args:
            key: Configuration key (snake_case)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return getattr(self, key, default)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings singleton."""
    return Settings()


# Create singleton instance - THIS IS THE KEY!
settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]