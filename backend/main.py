"""
Main entry point for the application.
Used to verify setup is working correctly.
"""

from src.config import get_settings
from src.infrastructure.database import Database
from src.logging_config import get_logger

logger = get_logger(__name__)


def init_app():
    """Initialize application."""
    settings = get_settings()
    
    logger.info(f"Initializing {settings.app_name}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug: {settings.debug}")
    
    # Create directories
    settings.ensure_directories()
    logger.info("Directories created/verified")
    
    # Initialize database
    db = Database()
    db.connect()
    db.create_tables()
    db.close()
    logger.info("Database initialized")
    
    return settings


if __name__ == "__main__":
    init_app()
    logger.info("Application ready")