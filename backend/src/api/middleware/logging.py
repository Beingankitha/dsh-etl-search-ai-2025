"""API middleware for cross-cutting concerns.

Provides:
- Structured request/response logging with observability
- Trace context propagation (W3C Trace Context)
- Performance monitoring
- Security headers
- Request ID generation and correlation
"""

from __future__ import annotations

import time
import uuid
import json
import logging
from typing import Callable, Optional, Any
from io import BytesIO

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.datastructures import MutableHeaders

from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced HTTP request/response logging with observability.
    
    Features:
    - Request/response logging with body (where possible)
    - Performance metrics (duration, size)
    - Trace context extraction and propagation (W3C Trace Context)
    - Request ID generation for correlation
    - OpenTelemetry span creation
    - Security: PII redaction in logs
    
    Attributes:
        tracer: OpenTelemetry tracer instance
        pii_patterns: Keys to redact from logs
    """
    
    # Keys to redact from logs (PII/security)
    PII_KEYS = {
        "password", "token", "api_key", "secret",
        "authorization", "cookie", "x-api-key",
    }
    
    def __init__(self, app: Callable) -> None:
        """Initialize middleware.
        
        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.tracer = trace.get_tracer(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request/response with logging and tracing.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response with updated headers
        """
        # Generate or extract request ID
        request_id = self._get_or_create_request_id(request)
        
        # Extract W3C Trace Context from headers
        trace_parent = request.headers.get("traceparent")
        trace_state = request.headers.get("tracestate")
        
        # Store request ID and trace context in request state
        request.state.request_id = request_id
        request.state.trace_parent = trace_parent
        
        # Create span for this request
        span_name = f"{request.method} {request.url.path}"
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set semantic attributes (OpenTelemetry standards)
                self._set_request_attributes(span, request, request_id)
                
                # Capture start time
                start_time = time.time()
                
                # Read request body (for logging, not affecting actual processing)
                request_body = await self._read_request_body(request)
                
                # Call next middleware/handler
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Set response attributes
                self._set_response_attributes(
                    span, response, duration, len(request_body)
                )
                
                # Add trace context headers to response
                headers = MutableHeaders(response.headers)
                if trace_parent:
                    headers["traceparent"] = trace_parent
                if trace_state:
                    headers["tracestate"] = trace_state
                headers["x-request-id"] = request_id
                
                # Log request/response (redact sensitive data)
                self._log_request_response(
                    request, response, request_body, duration, request_id
                )
                
                # Set span status based on HTTP status code
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.UNSET))
                else:
                    span.set_status(Status(StatusCode.OK))
                
                return response
                
            except Exception as exc:
                # Record exception in span
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                logger.error(
                    f"Request processing failed: {str(exc)}",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "method": request.method,
                    },
                    exc_info=True,
                )
                raise
    
    @staticmethod
    def _get_or_create_request_id(request: Request) -> str:
        """Extract or generate request ID from headers.
        
        Supports common header names:
        - X-Request-ID
        - X-Correlation-ID
        - Request-ID
        
        Args:
            request: HTTP request
            
        Returns:
            Request ID (existing or newly generated UUID)
        """
        for header in ["x-request-id", "x-correlation-id", "request-id"]:
            if header in request.headers:
                return request.headers[header]
        
        return str(uuid.uuid4())
    
    @staticmethod
    async def _read_request_body(request: Request) -> bytes:
        """Read request body without consuming it.
        
        Args:
            request: HTTP request
            
        Returns:
            Request body bytes
        """
        body = await request.body()
        
        # Store body in request for later access
        request._body = body
        
        # Create new receive callable that returns stored body
        async def receive():
            return {"type": "http.request", "body": body}
        
        request._receive = receive
        
        return body
    
    @staticmethod
    def _set_request_attributes(
        span: trace.Span,
        request: Request,
        request_id: str,
    ) -> None:
        """Set OpenTelemetry semantic attributes for request.
        
        Following OpenTelemetry HTTP semantic conventions.
        
        Args:
            span: OpenTelemetry span
            request: HTTP request
            request_id: Request ID for correlation
        """
        span.set_attributes({
            # HTTP semantic conventions
            "http.method": request.method,
            "http.url": str(request.url),
            "http.target": request.url.path,
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname or "unknown",
            "http.client_ip": RequestLoggingMiddleware._get_client_ip(request),
            
            # Custom attributes
            "request_id": request_id,
            "http.query_string": request.url.query or "",
        })
    
    @staticmethod
    def _set_response_attributes(
        span: trace.Span,
        response: Response,
        duration: float,
        request_size: int,
    ) -> None:
        """Set OpenTelemetry semantic attributes for response.
        
        Args:
            span: OpenTelemetry span
            response: HTTP response
            duration: Request duration in seconds
            request_size: Size of request body in bytes
        """
        try:
            response_size = int(response.headers.get("content-length", 0))
        except (ValueError, TypeError):
            response_size = 0
        
        span.set_attributes({
            # HTTP semantic conventions
            "http.status_code": response.status_code,
            "http.request_content_length": request_size,
            "http.response_content_length": response_size,
            
            # Performance metrics
            "http.duration_ms": int(duration * 1000),
        })
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request (handles proxies).
        
        Checks in order:
        1. X-Forwarded-For (proxy)
        2. X-Real-IP (nginx proxy)
        3. CF-Connecting-IP (Cloudflare)
        4. request.client.host
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _log_request_response(
        self,
        request: Request,
        response: Response,
        request_body: bytes,
        duration: float,
        request_id: str,
    ) -> None:
        """Log request/response with context and PII redaction.
        
        Args:
            request: HTTP request
            response: HTTP response
            request_body: Request body bytes
            duration: Duration in seconds
            request_id: Request ID for correlation
        """
        try:
            # Parse and redact request body if JSON
            request_body_dict = None
            if request_body and request.headers.get("content-type") == "application/json":
                try:
                    request_body_dict = json.loads(request_body)
                    request_body_dict = self._redact_sensitive_fields(request_body_dict)
                except json.JSONDecodeError:
                    request_body_dict = {"error": "invalid json"}
            
            # Log at appropriate level
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            
            log_msg = (
                f"{request.method} {request.url.path} "
                f"- {response.status_code} [{duration:.3f}s]"
            )
            
            logger.log(
                log_level,
                log_msg,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": int(duration * 1000),
                    "request_body": request_body_dict,
                    "query_params": dict(request.query_params),
                },
            )
        except Exception as e:
            logger.error(f"Error logging request/response: {e}", exc_info=True)
    
    @staticmethod
    def _redact_sensitive_fields(data: Any) -> Any:
        """Recursively redact sensitive fields from data.
        
        Redacts keys matching PII_KEYS pattern.
        
        Args:
            data: Data structure (dict, list, etc.)
            
        Returns:
            Data structure with sensitive fields redacted
        """
        if isinstance(data, dict):
            return {
                k: (
                    "[REDACTED]"
                    if any(
                        pii_key in k.lower()
                        for pii_key in RequestLoggingMiddleware.PII_KEYS
                    )
                    else RequestLoggingMiddleware._redact_sensitive_fields(v)
                )
                for k, v in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return type(data)(
                RequestLoggingMiddleware._redact_sensitive_fields(item)
                for item in data
            )
        return data


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Propagate W3C Trace Context headers.
    
    Ensures trace IDs are propagated across service boundaries
    following W3C Trace Context standard.
    
    Reference: https://www.w3.org/TR/trace-context/
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Propagate trace context to response.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response with trace context headers
        """
        # OpenTelemetry automatically handles trace context propagation
        # This middleware ensures headers are passed through
        
        response = await call_next(request)
        
        # Get current span context
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            
            # Set traceparent header (W3C standard)
            response.headers["traceparent"] = (
                f"00-{span_context.trace_id:032x}-"
                f"{span_context.span_id:016x}-"
                f"{'01' if span_context.is_remote else '00'}"
            )
        
        return response
