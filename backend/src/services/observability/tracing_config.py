"""OpenTelemetry configuration and initialization.

Sets up:
- OTLP gRPC exporter for trace visualization (modern standard)
- Trace provider with resource attributes
- Span processors for batching and export
- Global tracer configuration
"""

import logging
from dataclasses import dataclass
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader

logger = logging.getLogger(__name__)


@dataclass
class TraceConfig:
    """Configuration for distributed tracing."""
    
    service_name: str = "dsh-etl-search-ai"
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    jaeger_enabled: bool = True
    trace_sample_rate: float = 1.0  # 100% sampling (adjust for production)
    environment: str = "development"
    version: str = "0.1.0"


# Global state
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None
_initialized = False


def initialize_tracing(config: TraceConfig = None) -> TracerProvider:
    """
    Initialize OpenTelemetry with Jaeger exporter.
    
    Args:
        config: TraceConfig instance with settings
        
    Returns:
        Configured TracerProvider instance
    """
    global _tracer_provider, _meter_provider, _initialized
    
    if _initialized:
        logger.debug("Tracing already initialized")
        return _tracer_provider
    
    config = config or TraceConfig()
    
    # Create resource with service metadata
    resource = Resource.create({
        SERVICE_NAME: config.service_name,
        "environment": config.environment,
        "service.version": config.version,
    })
    
    # Create trace provider
    _tracer_provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter if enabled
    if config.jaeger_enabled:
        try:
            # Use OTLP gRPC exporter (modern standard, replaces deprecated Jaeger thrift)
            otlp_exporter = OTLPSpanExporter(
                endpoint=f"http://{config.jaeger_host}:4317",  # OTLP gRPC port
            )
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(
                f"OTLP exporter initialized: {config.jaeger_host}:4317"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize OTLP exporter: {e}. "
                "Traces will not be exported."
            )
    
    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Initialize metrics with Prometheus exporter
    try:
        prometheus_reader = PrometheusMetricReader()
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader]
        )
        metrics.set_meter_provider(_meter_provider)
        logger.info("Prometheus metrics exporter initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Prometheus exporter: {e}")
    
    _initialized = True
    logger.info("Distributed tracing initialized")
    
    return _tracer_provider


def get_tracer(name: str, version: str = "") -> trace.Tracer:
    """
    Get a tracer instance for the given module.
    
    Args:
        name: Module/service name (e.g., "src.services.etl")
        version: Optional version string
        
    Returns:
        Tracer instance
    """
    if not _initialized:
        initialize_tracing()
    
    return _tracer_provider.get_tracer(name, version)


def get_tracer_provider() -> TracerProvider:
    """Get the global tracer provider."""
    if not _initialized:
        initialize_tracing()
    return _tracer_provider


def get_meter(name: str, version: str = ""):
    """Get a meter instance for metrics."""
    if _meter_provider is None:
        logger.warning("Meter provider not initialized")
        return None
    return _meter_provider.get_meter(name, version)


def shutdown_tracing() -> None:
    """Gracefully shutdown tracing and flush spans."""
    global _tracer_provider, _initialized
    
    if _tracer_provider is None:
        return
    
    try:
        _tracer_provider.force_flush()
        _tracer_provider.shutdown()
        logger.info("Tracing shutdown complete")
    except Exception as e:
        logger.error(f"Error during tracing shutdown: {e}")
    finally:
        _initialized = False
        _tracer_provider = None
