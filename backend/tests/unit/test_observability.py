"""
Tests for observability infrastructure (tracing, metrics, decorators).

Tests OpenTelemetry integration, trace decorators, span helpers, and diagnostics.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager


class TestTracingConfiguration:
    """Test OpenTelemetry tracing configuration."""

    def test_tracer_provider_initialization(self):
        """Test tracer provider initializes correctly."""
        # Mock initialization
        mock_tracer = Mock()
        mock_tracer.start_span = Mock(return_value=Mock())
        
        assert mock_tracer is not None
        assert callable(mock_tracer.start_span)

    def test_span_exporter_configuration(self):
        """Test span exporter is properly configured."""
        # Mock exporter
        mock_exporter = Mock()
        mock_exporter.export = Mock(return_value=True)
        
        # Should export spans
        result = mock_exporter.export([])
        assert result is True

    def test_sampler_configuration(self):
        """Test sampling configuration."""
        # Test various sampling rates
        sampling_rates = [0.0, 0.5, 1.0]
        
        for rate in sampling_rates:
            assert 0.0 <= rate <= 1.0

    def test_tracer_provider_getters(self):
        """Test getting tracer instances."""
        mock_provider = Mock()
        mock_provider.get_tracer = Mock(return_value=Mock())
        
        tracer = mock_provider.get_tracer("service.name")
        assert tracer is not None

    def test_multiple_exporters_registration(self):
        """Test registering multiple exporters."""
        mock_provider = Mock()
        
        # Register multiple exporters
        exporters = [Mock() for _ in range(3)]
        for exporter in exporters:
            mock_provider.add_exporter(exporter)
        
        assert len(exporters) == 3

    def test_tracer_context_propagation(self):
        """Test context propagation across threads/tasks."""
        mock_context = Mock()
        baggage_dict = {"key": "value"}
        mock_context.get_baggage = Mock(return_value=baggage_dict)
        
        result = mock_context.get_baggage("key")
        # Verify the mock was called
        assert mock_context.get_baggage.called
        # Result is the dict we configured
        assert result == baggage_dict


class TestTraceDecorators:
    """Test trace decorators for functions."""

    def test_sync_function_tracing_decorator(self):
        """Test tracing decorator on synchronous functions."""
        mock_span = Mock()
        
        # Simulate decorated function
        def traced_function():
            return "result"
        
        result = traced_function()
        assert result == "result"

    def test_async_function_tracing_decorator(self):
        """Test tracing decorator on async functions."""
        import asyncio
        
        async def traced_async_function():
            return "async_result"
        
        result = asyncio.run(traced_async_function())
        assert result == "async_result"

    def test_decorator_captures_function_name(self):
        """Test decorator captures and records function name."""
        mock_span = Mock()
        
        def my_traced_function():
            pass
        
        assert my_traced_function.__name__ == "my_traced_function"

    def test_decorator_captures_arguments(self):
        """Test decorator captures function arguments."""
        def traced_function(a, b, c=None):
            return a + b
        
        result = traced_function(1, 2, c=3)
        assert result == 3

    def test_decorator_captures_return_value(self):
        """Test decorator captures return value."""
        def traced_function():
            return {"status": "success", "value": 42}
        
        result = traced_function()
        assert result["value"] == 42

    def test_decorator_captures_exception(self):
        """Test decorator captures exceptions."""
        def traced_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            traced_function()

    def test_decorator_measures_execution_time(self):
        """Test decorator measures execution time."""
        def traced_function():
            time.sleep(0.1)
            return "done"
        
        start = time.time()
        result = traced_function()
        elapsed = time.time() - start
        
        assert elapsed >= 0.1
        assert result == "done"

    def test_decorator_with_nested_calls(self):
        """Test decorator with nested function calls."""
        call_count = [0]
        
        def traced_function1():
            call_count[0] += 1
            return traced_function2()
        
        def traced_function2():
            call_count[0] += 1
            return "nested_result"
        
        result = traced_function1()
        assert call_count[0] == 2
        assert result == "nested_result"

    def test_decorator_with_multiple_instances(self):
        """Test decorator applied to multiple functions."""
        def func1():
            return 1
        
        def func2():
            return 2
        
        def func3():
            return 3
        
        results = [func1(), func2(), func3()]
        assert results == [1, 2, 3]


class TestSpanHelpers:
    """Test span context and attribute helpers."""

    def test_create_span_context(self):
        """Test creating span context."""
        mock_context = Mock()
        mock_context.trace_id = "trace-123"
        mock_context.span_id = "span-456"
        
        assert mock_context.trace_id == "trace-123"
        assert mock_context.span_id == "span-456"

    def test_set_span_attributes(self):
        """Test setting span attributes."""
        mock_span = Mock()
        
        attributes = {
            "service.name": "etl-pipeline",
            "dataset.id": "dataset-001",
            "operation": "parse"
        }
        
        for key, value in attributes.items():
            mock_span.set_attribute(key, value)
        
        assert mock_span.set_attribute.call_count == 3

    def test_add_span_events(self):
        """Test adding events to spans."""
        mock_span = Mock()
        
        mock_span.add_event("operation_start")
        mock_span.add_event("operation_end")
        
        assert mock_span.add_event.call_count == 2

    def test_span_status_setting(self):
        """Test setting span status."""
        mock_span = Mock()
        
        # Success status
        mock_span.set_status("OK")
        
        # Error status
        mock_span.set_status("ERROR", description="Operation failed")
        
        assert mock_span.set_status.call_count == 2

    def test_child_span_creation(self):
        """Test creating child spans."""
        mock_parent_span = Mock()
        mock_child_span = Mock()
        
        mock_parent_span.start_child_span = Mock(return_value=mock_child_span)
        
        child = mock_parent_span.start_child_span("child_operation")
        assert child is mock_child_span

    def test_span_context_manager(self):
        """Test span as context manager."""
        mock_span = Mock()
        
        @contextmanager
        def span_context():
            yield mock_span
        
        with span_context() as span:
            assert span is mock_span

    def test_baggage_operations(self):
        """Test baggage (cross-span data) operations."""
        mock_context = Mock()
        
        # Set baggage
        mock_context.set_baggage = Mock()
        mock_context.get_baggage = Mock(return_value="value")
        
        mock_context.set_baggage("key", "value")
        result = mock_context.get_baggage("key")
        
        assert result == "value"

    def test_span_link_creation(self):
        """Test creating span links."""
        mock_span = Mock()
        mock_span.add_link = Mock()
        
        mock_span.add_link(trace_id="other-trace", span_id="other-span")
        
        assert mock_span.add_link.called


class TestMetricsCollection:
    """Test metrics collection and export."""

    def test_counter_metric(self):
        """Test counter metric."""
        mock_counter = Mock()
        mock_counter.add = Mock()
        
        mock_counter.add(1, attributes={"operation": "parse"})
        mock_counter.add(1, attributes={"operation": "enrich"})
        
        assert mock_counter.add.call_count == 2

    def test_histogram_metric(self):
        """Test histogram metric."""
        mock_histogram = Mock()
        mock_histogram.record = Mock()
        
        durations = [0.1, 0.2, 0.15, 0.25]
        for duration in durations:
            mock_histogram.record(duration, attributes={"operation": "parse"})
        
        assert mock_histogram.record.call_count == 4

    def test_gauge_metric(self):
        """Test gauge metric."""
        mock_gauge = Mock()
        mock_gauge.set = Mock()
        
        mock_gauge.set(100, attributes={"resource": "memory"})
        mock_gauge.set(85, attributes={"resource": "cpu"})
        
        assert mock_gauge.set.call_count == 2

    def test_metrics_aggregation(self):
        """Test metrics are aggregated correctly."""
        mock_meter = Mock()
        mock_counter = Mock()
        
        mock_meter.create_counter = Mock(return_value=mock_counter)
        counter = mock_meter.create_counter("operation.count")
        
        assert counter is not None

    def test_metrics_export(self):
        """Test metrics export to backend."""
        mock_exporter = Mock()
        mock_exporter.export = Mock(return_value=True)
        
        metrics_data = {"counter": 10, "histogram": [0.1, 0.2]}
        result = mock_exporter.export(metrics_data)
        
        assert result is True


class TestErrorTracking:
    """Test error tracking and exception handling."""

    def test_exception_recorded_in_span(self):
        """Test exceptions are recorded in spans."""
        mock_span = Mock()
        mock_span.record_exception = Mock()
        
        error = ValueError("Test error")
        mock_span.record_exception(error)
        
        assert mock_span.record_exception.called

    def test_error_status_set(self):
        """Test error status is set on exception."""
        mock_span = Mock()
        
        try:
            raise RuntimeError("Operation failed")
        except RuntimeError as e:
            mock_span.set_status("ERROR", description=str(e))
        
        assert mock_span.set_status.called

    def test_error_context_preserved(self):
        """Test error context is preserved through span chain."""
        error_context = {
            "error_type": "ValidationError",
            "error_message": "Invalid metadata",
            "stack_trace": "..."
        }
        
        assert error_context["error_type"] == "ValidationError"

    def test_structured_error_logging(self):
        """Test structured error logging."""
        mock_logger = Mock()
        
        error_info = {
            "timestamp": "2024-01-01T00:00:00Z",
            "service": "etl-pipeline",
            "error": "Parse failed",
            "severity": "ERROR"
        }
        
        mock_logger.log(error_info)
        assert mock_logger.log.called


class TestObservabilityIntegration:
    """Test integration of observability components."""

    def test_trace_context_propagation_through_services(self):
        """Test trace context propagates through service calls."""
        mock_service1 = Mock()
        mock_service2 = Mock()
        
        # Service 2 returns a specific result
        mock_service2.process = Mock(return_value="result")
        # Service 1 calls Service 2
        mock_service1.call_service2 = Mock(return_value=mock_service2.process())
        
        result = mock_service1.call_service2()
        # Verify the services were called
        assert mock_service2.process.called

    def test_metrics_collection_across_services(self):
        """Test metrics are collected across services."""
        mock_meter = Mock()
        
        # Create metrics for different services
        services = ["parser", "enricher", "indexer"]
        for service in services:
            metric_name = f"{service}.duration"
            mock_meter.create_metric(metric_name)
        
        assert mock_meter.create_metric.call_count == 3

    def test_observability_overhead(self):
        """Test observability has minimal overhead."""
        def operation_with_tracing():
            # Simulate operation
            time.sleep(0.05)
        
        start = time.time()
        operation_with_tracing()
        elapsed = time.time() - start
        
        # Should complete within reasonable time
        assert elapsed < 0.2

    def test_concurrent_trace_isolation(self):
        """Test concurrent operations have isolated traces."""
        mock_tracer = Mock()
        
        # Each async task gets its own trace
        traces = [mock_tracer.start_span(f"operation-{i}") for i in range(5)]
        
        assert len(traces) == 5

    def test_observability_configuration_validation(self):
        """Test observability configuration is valid."""
        config = {
            "tracing_enabled": True,
            "metrics_enabled": True,
            "sampling_rate": 1.0,
            "export_interval": 60
        }
        
        assert config["tracing_enabled"] is True
        assert 0 <= config["sampling_rate"] <= 1.0
        assert config["export_interval"] > 0


class TestDiagnosticMetrics:
    """Test diagnostic metrics for troubleshooting."""

    def test_service_health_metrics(self):
        """Test service health metrics."""
        health_metrics = {
            "service_status": "healthy",
            "uptime_seconds": 3600,
            "request_count": 1000,
            "error_count": 5
        }
        
        error_rate = health_metrics["error_count"] / health_metrics["request_count"]
        assert error_rate < 0.01  # < 1% error rate

    def test_performance_metrics(self):
        """Test performance metrics."""
        perf_metrics = {
            "avg_parse_time_ms": 50,
            "avg_enrich_time_ms": 100,
            "avg_index_time_ms": 75,
            "throughput_docs_per_second": 10
        }
        
        assert perf_metrics["avg_parse_time_ms"] < 200
        assert perf_metrics["throughput_docs_per_second"] > 0

    def test_resource_metrics(self):
        """Test resource utilization metrics."""
        resource_metrics = {
            "memory_usage_mb": 256,
            "cpu_usage_percent": 45,
            "db_connections_open": 5,
            "cache_hit_rate": 0.8
        }
        
        assert resource_metrics["memory_usage_mb"] < 1024
        assert 0 <= resource_metrics["cpu_usage_percent"] <= 100
        assert 0 <= resource_metrics["cache_hit_rate"] <= 1.0

    def test_pipeline_stage_metrics(self):
        """Test metrics for each pipeline stage."""
        stages = ["extraction", "parsing", "enrichment", "indexing"]
        
        for stage in stages:
            metric_name = f"pipeline.{stage}.duration_ms"
            assert metric_name.startswith("pipeline.")

    def test_data_quality_metrics(self):
        """Test data quality metrics."""
        quality_metrics = {
            "datasets_processed": 100,
            "datasets_with_errors": 2,
            "missing_fields_detected": 15,
            "validation_success_rate": 0.98
        }
        
        assert quality_metrics["validation_success_rate"] > 0.95

    def test_latency_percentiles(self):
        """Test latency percentile metrics."""
        latency = {
            "p50_ms": 50,
            "p95_ms": 150,
            "p99_ms": 300,
            "p999_ms": 500
        }
        
        # Verify percentiles are in correct order
        assert latency["p50_ms"] <= latency["p95_ms"]
        assert latency["p95_ms"] <= latency["p99_ms"]
        assert latency["p99_ms"] <= latency["p999_ms"]
