"""Observability module - distributed tracing and performance monitoring.

Provides:
- OpenTelemetry integration for distributed tracing
- Jaeger exporter for trace visualization
- Custom span attributes and metrics
- Performance monitoring decorators
"""

from .tracing_config import (
    TraceConfig,
    initialize_tracing,
    get_tracer,
    get_tracer_provider,
    shutdown_tracing,
)
from .trace_decorators import (
    trace_async_function,
    trace_sync_function,
    trace_method,
    trace_async_method,
)
from .span_helpers import (
    with_span,
    set_span_attributes,
    add_span_event,
    record_exception,
    get_current_span,
)

__all__ = [
    "TraceConfig",
    "initialize_tracing",
    "get_tracer",
    "get_tracer_provider",
    "shutdown_tracing",
    "trace_async_function",
    "trace_sync_function",
    "trace_method",
    "trace_async_method",
    "with_span",
    "set_span_attributes",
    "add_span_event",
    "record_exception",
    "get_current_span",
]
