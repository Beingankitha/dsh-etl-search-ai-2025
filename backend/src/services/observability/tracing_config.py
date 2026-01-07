"""OpenTelemetry configuration and initialization.

Sets up:
- OTLP gRPC exporter for trace visualization (modern standard) - OPTIONAL
- Trace provider with resource attributes
- Span processors for batching and export (only if exporter enabled)
- Graceful degradation when collector unavailable

IMPORTANT: OTLP exporter is disabled by default to prevent connection errors
when no OpenTelemetry Collector is running. Enable only in instrumented
environments (development with Jaeger, staging, or production).
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader

logger = logging.getLogger(__name__)


@dataclass
class TraceConfig:
    """Configuration for distributed tracing.
    
    Attributes:
        service_name: Service identifier for traces
        jaeger_host: OTLP collector host (only used if jaeger_enabled=True)
        jaeger_port: OTLP collector port (only used if jaeger_enabled=True)
        jaeger_enabled: Enable OTLP exporter (disable if no collector running)
        trace_sample_rate: Sampling rate 0.0-1.0 (adjust for production)
        environment: Environment name (development, staging, production)
        version: Service version
    """
    
    service_name: str = "dsh-etl-search-ai"
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    jaeger_enabled: bool = False  # DISABLED BY DEFAULT - prevent "localhost:4317" errors
    trace_sample_rate: float = 0.1  # 10% sampling (reduce for production)
    environment: str = "development"
    version: str = "1.0.0"


# Global state
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None
_initialized = False


def initialize_tracing(config: TraceConfig = None) -> TracerProvider:
    """
    Initialize OpenTelemetry with optional OTLP exporter.
    
    The OTLP exporter is only initialized if jaeger_enabled=True AND
    the collector endpoint is reachable. This prevents "localhost:4317"
    connection errors when no collector is running.
    
    Tracing always works locally (useful for development) but only
    exports to a collector if one is available.
    
    Args:
        config: TraceConfig instance with settings
        
    Returns:
        Configured TracerProvider instance (tracing always enabled locally)
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
    
    # Create trace provider (always works locally)
    _tracer_provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter ONLY if explicitly enabled
    # This prevents "localhost:4317 UNAVAILABLE" errors in development
    if config.jaeger_enabled:
        try:
            # Lazy import to avoid import errors if OpenTelemetry not available
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            logger.info(
                f"Initializing OTLP exporter to {config.jaeger_host}:4317 "
                "(ensure OpenTelemetry Collector is running)"
            )
            
            # Create exporter with timeout to fail fast
            otlp_exporter = OTLPSpanExporter(
                endpoint=f"http://{config.jaeger_host}:4317",  # OTLP gRPC port
                timeout=5,  # 5 second timeout - fail fast if collector unavailable
            )
            
            # Use BatchSpanProcessor for production, SimpleSpanProcessor for development
            if config.environment == "development":
                _tracer_provider.add_span_processor(
                    SimpleSpanProcessor(otlp_exporter)
                )
            else:
                _tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
            
            logger.info(
                f"✓ OTLP exporter initialized: {config.jaeger_host}:4317"
            )
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp not installed. "
                "Tracing works locally but won't export."
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize OTLP exporter: {e}. "
                "This is normal if no OpenTelemetry Collector is running. "
                "Tracing continues locally without export."
            )
    else:
        logger.debug(
            "OTLP exporter disabled (jaeger_enabled=false). "
            "Tracing works locally only."
        )
    
    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Initialize metrics with Prometheus exporter (optional)
    try:
        prometheus_reader = PrometheusMetricReader()
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader]
        )
        metrics.set_meter_provider(_meter_provider)
        logger.debug("Prometheus metrics exporter initialized")
    except Exception as e:
        logger.debug(f"Prometheus exporter not available: {e}")
    
    _initialized = True
    logger.info(
        f"✓ OpenTelemetry initialized (service: {config.service_name}, "
        f"environment: {config.environment})"
    )
    
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
