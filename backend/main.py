"""
Main entry point for the application.
Used to verify setup is working correctly.
"""

from src.config import get_settings
from src.logging_config import setup_logging, get_logger


def main() -> None:
    """Main function to test configuration and logging."""
    # Load settings
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.log_level)
    
    # Get logger
    logger = get_logger(__name__)
    
    # Log startup information
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.debug("This is a debug message (only visible if LOG_LEVEL=DEBUG)")
    logger.info(f"Database path: {settings.database_path}")
    logger.info(f"Vector store path: {settings.chroma_path}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Ollama model: {settings.ollama_model}")
    logger.info("Configuration loaded successfully!")


if __name__ == "__main__":
    main()