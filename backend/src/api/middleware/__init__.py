"""API middleware package.

Provides cross-cutting concerns for FastAPI:
- Request/response logging with observability
- Trace context propagation
- Performance monitoring
"""

from .logging import RequestLoggingMiddleware, TraceContextMiddleware

__all__ = ["RequestLoggingMiddleware", "TraceContextMiddleware"]
