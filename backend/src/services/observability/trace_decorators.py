"""Decorators for automatic tracing of functions and methods."""

import functools
import logging
import inspect
from typing import Callable, Any, TypeVar, Optional

from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode

from .tracing_config import get_tracer

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])

# Tracer instance
_tracer = None


def _get_tracer():
    """Lazy-load tracer."""
    global _tracer
    if _tracer is None:
        _tracer = get_tracer(__name__)
    return _tracer


def trace_async_function(
    span_name: Optional[str] = None,
    attributes: Optional[dict] = None,
):
    """
    Decorator for tracing async functions.
    
    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Static attributes to attach to span
        
    Example:
        @trace_async_function(attributes={"service": "etl"})
        async def process_dataset(identifier: str):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = _get_tracer()
            span_name_final = span_name or func.__name__
            
            # Extract identifiers from args/kwargs for span context
            span_attrs = attributes.copy() if attributes else {}
            span_attrs["function"] = func.__name__
            
            # Add relevant function arguments to span
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Add common ETL identifiers to span
            if "identifier" in bound_args.arguments:
                span_attrs["identifier"] = str(bound_args.arguments["identifier"])
            if "url" in bound_args.arguments:
                span_attrs["url"] = str(bound_args.arguments["url"])[:100]  # Limit length
            
            with tracer.start_as_current_span(span_name_final) as span:
                # Set attributes
                for key, value in span_attrs.items():
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        else:
                            span.set_attribute(key, str(value))
                    except Exception as e:
                        logger.debug(f"Failed to set span attribute {key}: {e}")
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
        
        return wrapper  # type: ignore
    
    return decorator


def trace_sync_function(
    span_name: Optional[str] = None,
    attributes: Optional[dict] = None,
):
    """
    Decorator for tracing synchronous functions.
    
    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Static attributes to attach to span
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = _get_tracer()
            span_name_final = span_name or func.__name__
            
            span_attrs = attributes.copy() if attributes else {}
            span_attrs["function"] = func.__name__
            
            # Extract arguments
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            if "identifier" in bound_args.arguments:
                span_attrs["identifier"] = str(bound_args.arguments["identifier"])
            if "url" in bound_args.arguments:
                span_attrs["url"] = str(bound_args.arguments["url"])[:100]
            
            with tracer.start_as_current_span(span_name_final) as span:
                for key, value in span_attrs.items():
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        else:
                            span.set_attribute(key, str(value))
                    except Exception as e:
                        logger.debug(f"Failed to set span attribute {key}: {e}")
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
        
        return wrapper  # type: ignore
    
    return decorator


def trace_method(
    span_name: Optional[str] = None,
    attributes: Optional[dict] = None,
):
    """Decorator for tracing class methods (sync)."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            tracer = _get_tracer()
            span_name_final = span_name or f"{self.__class__.__name__}.{func.__name__}"
            
            span_attrs = attributes.copy() if attributes else {}
            span_attrs["class"] = self.__class__.__name__
            span_attrs["method"] = func.__name__
            
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            if "identifier" in bound_args.arguments:
                span_attrs["identifier"] = str(bound_args.arguments["identifier"])
            
            with tracer.start_as_current_span(span_name_final) as span:
                for key, value in span_attrs.items():
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        else:
                            span.set_attribute(key, str(value))
                    except Exception as e:
                        logger.debug(f"Failed to set span attribute {key}: {e}")
                
                try:
                    result = func(self, *args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
        
        return wrapper  # type: ignore
    
    return decorator


def trace_async_method(
    span_name: Optional[str] = None,
    attributes: Optional[dict] = None,
):
    """Decorator for tracing async class methods."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            tracer = _get_tracer()
            span_name_final = span_name or f"{self.__class__.__name__}.{func.__name__}"
            
            span_attrs = attributes.copy() if attributes else {}
            span_attrs["class"] = self.__class__.__name__
            span_attrs["method"] = func.__name__
            
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            if "identifier" in bound_args.arguments:
                span_attrs["identifier"] = str(bound_args.arguments["identifier"])
            
            with tracer.start_as_current_span(span_name_final) as span:
                for key, value in span_attrs.items():
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        else:
                            span.set_attribute(key, str(value))
                    except Exception as e:
                        logger.debug(f"Failed to set span attribute {key}: {e}")
                
                try:
                    result = await func(self, *args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
        
        return wrapper  # type: ignore
    
    return decorator
