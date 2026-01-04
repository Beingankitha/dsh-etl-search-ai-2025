"""
FastAPI application factory and configuration.

Creates the FastAPI app with:
- CORS middleware
- API routers
- Error handlers
- Request/response logging
"""

from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings
from src.logging_config import get_logger
from src.api.routes import health_router, search_router, datasets_router

logger = get_logger(__name__)


class ErrorDetail(dict):
    """Standard error response format."""
    pass


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Callable:
        import time
        
        # Log request
        logger.debug(f"{request.method} {request.url.path}")
        
        # Process request
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        # Log response
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
        
        return response


def create_app(settings=None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        settings: Application settings (uses default if None)
        
    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()
    
    logger.info(f"Creating FastAPI application: {settings.app_name}")
    
    # Create app with metadata
    app = FastAPI(
        title=settings.app_name,
        description="Semantic search and discovery for environmental datasets",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # ========================================================================
    # Middleware
    # ========================================================================
    
    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",      # Development frontend
            "http://localhost:5173",      # SvelteKit dev server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # ========================================================================
    # Lifespan Events
    # ========================================================================
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize on application startup."""
        logger.info(f"Starting {settings.app_name}")
        logger.info(f"Environment: {settings.app_env}")
        logger.info(f"Debug mode: {settings.debug}")
        settings.ensure_directories()
        logger.info("Application startup complete")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown."""
        logger.info("Shutting down application")
    
    # ========================================================================
    # Routes
    # ========================================================================
    
    # Health check endpoints (no /api prefix)
    app.include_router(health_router)
    
    # API v1 endpoints
    app.include_router(search_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    
    # ========================================================================
    # Root Routes
    # ========================================================================
    
    @app.get("/")
    async def root():
        """API root with metadata."""
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api": "/api",
        }
    
    # ========================================================================
    # Error Handlers
    # ========================================================================
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "INTERNAL_ERROR",
            }
        )
    
    logger.info(f"FastAPI application created successfully")
    
    return app


# Create default app instance for uvicorn
settings = get_settings()
app = create_app(settings)
