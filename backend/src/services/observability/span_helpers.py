"""Helper functions for working with OpenTelemetry spans."""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Optional, Iterator

from opentelemetry import trace, context as otel_context

logger = logging.getLogger(__name__)


def with_span(
    span_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> contextmanager:
    """
    Context manager for creating spans programmatically.
    
    Args:
        span_name: Name of the span
        attributes: Dictionary of attributes to set on span
        
    Returns:
        Context manager that yields the span
        
    Example:
        with with_span("process_dataset", {"identifier": "abc123"}):
            # Do work here
    """
    @contextmanager
    def _span_context() -> Iterator:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(span_name) as span:
            if attributes:
                set_span_attributes(span, attributes)
            yield span
    
    return _span_context()


def set_span_attributes(span: trace.Span, attributes: Dict[str, Any]) -> None:
    """
    Safely set multiple attributes on a span.
    
    Args:
        span: The span to set attributes on
        attributes: Dictionary of attribute name/value pairs
        
    Example:
        attrs = {
            "identifier": "be0bdc0e",
            "format": "xml",
            "status": "success"
        }
        set_span_attributes(span, attrs)
    """
    for key, value in attributes.items():
        try:
            if value is None:
                continue
            
            # OpenTelemetry supports specific types
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(key, value)
            elif isinstance(value, (list, tuple)):
                # Convert to comma-separated string for simple lists
                span.set_attribute(key, str(value))
            else:
                # Convert objects to string representation
                span.set_attribute(key, str(value))
        except Exception as e:
            logger.debug(f"Failed to set span attribute '{key}': {e}")


def add_span_event(
    span: trace.Span,
    event_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add an event to the current span.
    
    Args:
        span: The span to add event to
        event_name: Name of the event (e.g., "cache_hit", "download_started")
        attributes: Optional attributes for the event
        
    Example:
        add_span_event(span, "cache_hit", {"cache_key": "xml_metadata"})
        add_span_event(span, "download_started")
    """
    try:
        if attributes:
            span.add_event(event_name, attributes=attributes)
        else:
            span.add_event(event_name)
    except Exception as e:
        logger.debug(f"Failed to add span event '{event_name}': {e}")


def record_exception(
    span: trace.Span,
    exception: Exception,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record an exception on the current span.
    
    Args:
        span: The span to record exception on
        exception: The exception to record
        attributes: Optional additional attributes
        
    Example:
        try:
            # do work
        except IOError as e:
            record_exception(span, e, {"file_path": "/data/file.txt"})
    """
    try:
        if attributes:
            set_span_attributes(span, attributes)
        span.record_exception(exception)
    except Exception as e:
        logger.debug(f"Failed to record exception on span: {e}")


def get_current_span() -> trace.Span:
    """Get the currently active span."""
    return trace.get_current_span()


def set_span_status_ok(span: trace.Span) -> None:
    """Mark span as successful."""
    from opentelemetry.trace import Status, StatusCode
    span.set_status(Status(StatusCode.OK))


def set_span_status_error(span: trace.Span, description: str = "") -> None:
    """Mark span as failed with optional error description."""
    from opentelemetry.trace import Status, StatusCode
    span.set_status(Status(StatusCode.ERROR, description))


@contextmanager
def trace_context_with_baggage(key: str, value: str) -> Iterator:
    """
    Context manager to set OpenTelemetry baggage (cross-process context).
    
    Baggage allows passing context across service boundaries.
    
    Args:
        key: Baggage key (e.g., "request_id")
        value: Baggage value
        
    Example:
        with trace_context_with_baggage("request_id", "req-12345"):
            # This request_id is available to all downstream services
    """
    from opentelemetry.baggage import set_baggage
    
    token = set_baggage(key, value)
    try:
        yield
    finally:
        # Cleanup handled by context manager
        pass
