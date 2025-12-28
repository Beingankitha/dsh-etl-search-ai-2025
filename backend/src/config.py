"""
Application configuration using Pydantic Settings.
Loads values from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path

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

    # Database
    database_path: str = "./data/datasets.db"

    # Vector Store
    chroma_path: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Logging
    log_level: str = "INFO"

    @property
    def database_dir(self) -> Path:
        return Path(self.database_path).parent


@lru_cache
def get_settings() -> Settings:
    return Settings()