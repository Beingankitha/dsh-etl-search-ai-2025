"""
Custom exception classes for API layer.

Provides structured exception hierarchy following clean architecture principles:
- Single Responsibility: Each exception has one concern
- Type Safety: Proper status codes and error codes
- Semantic Clarity: Error types map to HTTP status codes
- Observability: All exceptions include trace context capability

Following OpenTelemetry semantic conventions for error recording.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes following REST conventions."""
    
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    SEARCH_ERROR = "SEARCH_ERROR"


@dataclass
class ErrorResponse:
    """Structured error response format.
    
    Attributes:
        detail: Human-readable error message
        error_code: Machine-readable error code (for clients)
        trace_id: OpenTelemetry trace ID for log correlation
        timestamp: ISO 8601 timestamp of error
        request_id: Optional request ID for tracking
    """
    detail: str
    error_code: str
    trace_id: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {
            k: v for k, v in {
                "detail": self.detail,
                "error_code": self.error_code,
                "trace_id": self.trace_id,
                "timestamp": self.timestamp,
                "request_id": self.request_id,
            }.items()
            if v is not None
        }


class APIException(Exception):
    """Base exception for all API-level errors.
    
    Provides:
    - HTTP status code
    - Machine-readable error code
    - Structured error response
    - Support for exception chaining
    
    Example:
        raise APIException(
            status_code=400,
            detail="Invalid query parameter",
            error_code=ErrorCode.VALIDATION_ERROR
        )
    """
    
    status_code: int = 500
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    
    def __init__(
        self,
        detail: str,
        status_code: Optional[int] = None,
        error_code: Optional[ErrorCode] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize API exception.
        
        Args:
            detail: Human-readable error message
            status_code: HTTP status code (uses class default if None)
            error_code: Machine-readable error code (uses class default if None)
            cause: Original exception (for chaining)
        """
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code or self.status_code
        self.error_code = error_code or self.error_code
        self.cause = cause
    
    def to_response(
        self,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ErrorResponse:
        """Convert exception to structured response.
        
        Args:
            trace_id: OpenTelemetry trace ID for correlation
            request_id: Request ID for tracking
            
        Returns:
            ErrorResponse with all context
        """
        from datetime import datetime, timezone
        
        return ErrorResponse(
            detail=self.detail,
            error_code=self.error_code.value,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        )


class ValidationError(APIException):
    """Raised when request validation fails.
    
    HTTP Status: 422 Unprocessable Entity
    
    Example:
        raise ValidationError(
            detail="Query must be at least 3 characters",
            error_code=ErrorCode.VALIDATION_ERROR
        )
    """
    status_code = 422
    error_code = ErrorCode.VALIDATION_ERROR


class NotFoundError(APIException):
    """Raised when requested resource is not found.
    
    HTTP Status: 404 Not Found
    
    Example:
        raise NotFoundError(
            detail=f"Dataset with id '{dataset_id}' not found"
        )
    """
    status_code = 404
    error_code = ErrorCode.NOT_FOUND


class ConflictError(APIException):
    """Raised when resource already exists or state conflict.
    
    HTTP Status: 409 Conflict
    
    Example:
        raise ConflictError(
            detail="Dataset with this identifier already exists"
        )
    """
    status_code = 409
    error_code = ErrorCode.CONFLICT


class UnauthorizedError(APIException):
    """Raised when authentication is required or invalid.
    
    HTTP Status: 401 Unauthorized
    
    Example:
        raise UnauthorizedError(
            detail="Authentication required"
        )
    """
    status_code = 401
    error_code = ErrorCode.UNAUTHORIZED


class ForbiddenError(APIException):
    """Raised when user lacks permissions.
    
    HTTP Status: 403 Forbidden
    
    Example:
        raise ForbiddenError(
            detail="You do not have permission to perform this action"
        )
    """
    status_code = 403
    error_code = ErrorCode.FORBIDDEN


class SearchServiceException(APIException):
    """Raised when search operation fails.
    
    HTTP Status: 500 Internal Server Error
    
    Example:
        raise SearchServiceException(
            detail="Failed to execute semantic search",
            cause=original_exception
        )
    """
    status_code = 500
    error_code = ErrorCode.SEARCH_ERROR


class DatabaseException(APIException):
    """Raised when database operation fails.
    
    HTTP Status: 500 Internal Server Error
    
    Example:
        raise DatabaseException(
            detail="Failed to retrieve datasets from database",
            cause=sqlite_exception
        )
    """
    status_code = 500
    error_code = ErrorCode.DATABASE_ERROR


class ServiceUnavailableException(APIException):
    """Raised when external service is unavailable.
    
    HTTP Status: 503 Service Unavailable
    
    Example:
        raise ServiceUnavailableException(
            detail="Vector database is temporarily unavailable"
        )
    """
    status_code = 503
    error_code = ErrorCode.SERVICE_UNAVAILABLE
