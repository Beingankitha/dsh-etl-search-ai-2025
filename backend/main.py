# """
# Main entry point for the application.
# Used to verify setup is working correctly.
# """

# from src.config import get_settings
# from src.infrastructure.database import Database
# from src.logging_config import get_logger

# logger = get_logger(__name__)


# def init_app():
#     """Initialize application."""
#     settings = get_settings()
    
#     logger.info(f"Initializing {settings.app_name}")
#     logger.info(f"Environment: {settings.app_env}")
#     logger.info(f"Debug: {settings.debug}")
    
#     # Create directories
#     settings.ensure_directories()
#     logger.info("Directories created/verified")
    
#     # Initialize database
#     db = Database()
#     db.connect()
#     db.create_tables()
#     db.close()
#     logger.info("Database initialized")
    
#     return settings


# if __name__ == "__main__":
#     init_app()
#     logger.info("Application ready")

"""
Main entry point for FastAPI server.

This script starts the FastAPI application for the Dataset Search & Discovery API.

Usage:
    uv run python main.py                    # Run on default host/port
    uv run uvicorn main:app --reload         # Run with auto-reload
    uv run python main.py --host 0.0.0.0 --port 8000
"""
 

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import settings  # Import settings INSTANCE, not Settings class
from src.logging_config import get_logger
from src.infrastructure.database import Database
from src.services.observability import initialize_tracing, shutdown_tracing, TraceConfig

logger = get_logger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize tracing
    try:
        trace_config = TraceConfig(
            service_name=settings.jaeger_service_name,
            jaeger_host=settings.jaeger_host,
            jaeger_port=settings.jaeger_port,
            jaeger_enabled=settings.jaeger_enabled,
            environment=settings.jaeger_environment,
        )
        initialize_tracing(trace_config)
        logger.info("✓ Distributed tracing initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Initialize database
    db_manager = Database(settings.database_path)
    db_manager.create_tables()
    logger.info("Database initialized")
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    try:
        shutdown_tracing()
        logger.info("✓ Distributed tracing shutdown")
    except Exception as e:
        logger.warning(f"Error during tracing shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="CEH Dataset Discovery System with Semantic Search and AI Chat",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DSH ETL Search AI API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )