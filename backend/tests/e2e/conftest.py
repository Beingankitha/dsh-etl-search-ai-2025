"""
Pytest configuration and shared fixtures for E2E tests.

Disables observability/tracing during tests to avoid hangs.
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_tracing():
    """Disable distributed tracing during tests."""
    # Disable Jaeger tracing
    os.environ["JAEGER_ENABLED"] = "false"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    
    # Set very short timeout for OTLP exporter in case it still tries to run
    os.environ["OTEL_EXPORTER_OTLP_TIMEOUT"] = "1"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:9999"  # Non-existent port


@pytest.fixture(scope="session", autouse=True)
def suppress_warnings():
    """Suppress known warnings during tests."""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    # Suppress gRPC warnings
    warnings.filterwarnings("ignore", message=".*grpc.*")
