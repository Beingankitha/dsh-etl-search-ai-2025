"""
FastAPI application factory and configuration.

Creates a production-ready FastAPI app with:
- OpenTelemetry instrumentation for distributed tracing
- Structured request/response logging with correlation IDs
- Comprehensive exception handling with semantic error codes
- CORS middleware for frontend integration
- Health check endpoints for deployment/monitoring
- API routers organized by domain

Architecture Principles:
- Dependency Injection: Services injected via FastAPI Depends()
- Separation of Concerns: Routers isolated by domain
- Observable: All requests traced and logged with correlation IDs
- Resilient: Graceful error handling with structured responses
- Type-Safe: Full Pydantic validation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from opentelemetry import trace

from src.config import get_settings
from src.logging_config import get_logger, setup_logging
from src.services.observability.tracing_config import initialize_tracing, shutdown_tracing
from src.api.middleware.logging import RequestLoggingMiddleware, TraceContextMiddleware
from src.api.exceptions import APIException, ErrorResponse
from src.api.routes import health_router, search_router, datasets_router, chat_router

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


def create_app(settings: Optional[object] = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Creates a production-ready application with:
    - OpenTelemetry tracing integration
    - Structured logging with correlation IDs
    - Comprehensive exception handling
    - CORS for frontend development
    - Health monitoring
    
    Architecture follows:
    - Clean Architecture: Clear separation between layers
    - SOLID Principles: Single responsibility, Open/closed
    - DI Pattern: Dependencies injected, not created
    - Observable: All operations traced and logged
    
    Args:
        settings: Application settings (uses default from config if None)
        
    Returns:
        Configured FastAPI application ready for deployment
        
    Raises:
        Exception: If critical initialization fails (logged before raising)
    """
    if settings is None:
        settings = get_settings()
    
    # Initialize logging system
    setup_logging(
        log_level=settings.get("log_level", "INFO"),
        log_file_path=settings.get("log_file_path", "logs/dsh_etl_search_ai.log")
    )
    
    logger.info(f"Creating FastAPI application: {settings.app_name}")
    logger.debug(f"Environment: {settings.environment}, Debug: {settings.debug}")
    
    # Initialize distributed tracing (OpenTelemetry)
    try:
        initialize_tracing()
        logger.info("OpenTelemetry tracing initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}. Continuing without tracing.")
    
    # Create FastAPI app with metadata
    app = FastAPI(
        title=settings.app_name,
        description="Semantic search and discovery for environmental datasets",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # ========================================================================
    # Middleware Configuration
    # ========================================================================
    
    # Add CORS middleware LAST (executes FIRST in the middleware chain)
    logger.debug("Configuring CORS middleware")
    
    # Determine allowed origins based on environment
    if settings.environment == "production":
        # Production: Be strict with origins, read from environment
        allowed_origins = [
            origin.strip() 
            for origin in (
                settings.get("cors_origins", "https://your-domain.com")
                .split(",")
            )
            if origin.strip()
        ]
        logger.info(f"Production CORS origins: {allowed_origins}")
        
        # Warn if still using placeholder
        if any("your-domain.com" in origin for origin in allowed_origins):
            logger.warning("⚠️  Production CORS origins contain placeholder domain!")
    else:
        # Development: Allow all localhost variants and common dev ports
        allowed_origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
            "http://127.0.0.1:5177",
            "http://[::1]",  # IPv6 localhost
            "http://[::1]:3000",
            "http://[::1]:5173",
            "http://[::1]:5174",
            "http://[::1]:5175",
            "http://[::1]:5176",
            "http://[::1]:5177",
        ]
        logger.debug(f"Development CORS enabled for {len(allowed_origins)} origins")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "traceparent", "tracestate"],
        max_age=3600,  # Cache preflight for 1 hour
    )
    
    # Add trace context middleware (propagates W3C Trace Context)
    logger.debug("Adding trace context middleware")
    app.add_middleware(TraceContextMiddleware)
    
    # Add enhanced logging middleware (request/response logging + spans)
    logger.debug("Adding request logging middleware")
    app.add_middleware(RequestLoggingMiddleware)
    
    # ========================================================================
    # Lifespan Events (Application Startup/Shutdown)
    # ========================================================================
    
    @app.on_event("startup")
    async def on_startup():
        """Initialize resources on application startup.
        
        Lifecycle:
        1. Log startup
        2. Ensure directories exist
        3. Initialize database connections (if needed)
        4. Warm up caches
        """
        logger.info("=" * 70)
        logger.info(f"Starting {settings.app_name}")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug Mode: {settings.debug}")
        logger.info(f"Log Level: {settings.get('log_level', 'INFO')}")
        logger.info("=" * 70)
        
        # Ensure required directories exist
        try:
            settings.ensure_directories()
            logger.info("Required directories initialized")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
    
    @app.on_event("shutdown")
    async def on_shutdown():
        """Clean up resources on application shutdown.
        
        Lifecycle:
        1. Close database connections
        2. Flush OpenTelemetry spans
        3. Log shutdown
        """
        logger.info("Shutting down application")
        try:
            shutdown_tracing()
            logger.info("Tracing shutdown complete")
        except Exception as e:
            logger.error(f"Error during tracing shutdown: {e}")
        logger.info("Application shutdown complete")
    
    # ========================================================================
    # Exception Handlers
    # ========================================================================
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle structured API exceptions.
        
        Converts APIException to structured JSON response with:
        - HTTP status code
        - Machine-readable error code
        - Human-readable detail
        - Trace ID (for log correlation)
        - Timestamp
        
        Args:
            request: HTTP request
            exc: APIException instance
            
        Returns:
            JSONResponse with error details
        """
        # Extract trace ID from request state
        trace_id: Optional[str] = getattr(request.state, "trace_id", None)
        if not trace_id:
            span = trace.get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                trace_id = f"{span_context.trace_id:032x}"
        
        # Extract request ID
        request_id: Optional[str] = getattr(request.state, "request_id", None)
        
        # Create error response
        error_response = exc.to_response(
            trace_id=trace_id,
            request_id=request_id,
        )
        
        # Log error with context
        logger.warning(
            f"{exc.status_code} {exc.error_code.value}: {exc.detail}",
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.error_code.value,
            },
        )
        
        # Record in current span if available
        span = trace.get_current_span()
        if span and span.is_recording():
            span.add_event(
                "API Error",
                attributes={
                    "error.type": exc.error_code.value,
                    "error.message": exc.detail,
                    "http.status_code": exc.status_code,
                },
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions.
        
        Converts any unhandled exception to structured JSON response.
        Logs full stack trace for debugging while returning generic message to client.
        
        Args:
            request: HTTP request
            exc: Unhandled exception
            
        Returns:
            JSONResponse with generic error
        """
        # Extract context
        trace_id: Optional[str] = getattr(request.state, "trace_id", None)
        if not trace_id:
            span = trace.get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                trace_id = f"{span_context.trace_id:032x}"
        
        request_id: Optional[str] = getattr(request.state, "request_id", None)
        
        # Log full exception with stack trace (NEVER send to client)
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,  # Include full stack trace
        )
        
        # Record in span
        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(exc)
        
        # Return generic error response (never expose internal details!)
        error_response = ErrorResponse(
            detail="Internal server error. Please contact support with trace ID.",
            error_code="INTERNAL_ERROR",
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.to_dict(),
        )
    
    # ========================================================================
    # API Routes
    # ========================================================================
    
    logger.debug("Registering API routes")
    
    # Health check endpoints (no /api prefix, used by deployment/monitoring)
    app.include_router(health_router)
    
    # API v1 endpoints (grouped under /api prefix)
    app.include_router(search_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    
    # ========================================================================
    # Root Endpoint
    # ========================================================================
    
    @app.get("/")
    async def root():
        """API root endpoint with metadata.
        
        Returns:
            Service metadata and endpoint documentation
        """
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "environment": settings.environment,
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "search": "/api/search",
                "datasets": "/api/datasets",
                "chat": "/api/chat",
            },
        }
    
    logger.info("FastAPI application initialized successfully")
    logger.info(f"Available endpoints: /health, /docs, /api/search, /api/datasets, /api/chat")
    
    return app


# ============================================================================
# Default App Instance
# ============================================================================

# Create default app instance for uvicorn
# uvicorn main:app --reload
settings = get_settings()
app = create_app(settings)
