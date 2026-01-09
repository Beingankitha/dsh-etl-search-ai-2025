"""
OBSERVABILITY INTEGRATION & TESTING PLAN
==========================================

This document outlines the complete integration of distributed tracing observability
into the existing ETL system and a comprehensive testing strategy.

## PART 1: FILES THAT NEED UPDATES

### Tier 1: Core Infrastructure (CRITICAL)
These files MUST be updated for tracing to work:

1. **src/config.py**
   - Add TraceConfig settings from environment variables
   - Add methods to initialize tracing
   - Coordinates tracing configuration with app startup

2. **src/logging_config.py**
   - Update get_logger() to work with OpenTelemetry
   - Ensure log messages include trace IDs for correlation
   - Add context correlation IDs

3. **main.py**
   - Initialize tracing in lifespan startup event
   - Shutdown tracing gracefully on shutdown
   - Add tracing middleware to FastAPI app

4. **src/cli.py**
   - Initialize tracing in etl command before pipeline runs
   - Shutdown tracing after ETL completes
   - Add trace context to CLI output for debugging

### Tier 2: Service Layer (HIGH)
Add decorators to main orchestrators:

5. **src/services/etl/etl_service.py** ✓ (ALREADY STARTED)
   - @trace_async_method on run_pipeline()
   - @trace_async_method on _extract_phase()
   - @trace_async_method on _transform_and_load_phase()
   - @trace_async_method on _process_supporting_documents()

6. **src/services/etl/metadata_cache.py**
   - @trace_async_method on get()
   - @trace_sync_method on set()
   - Track cache hit/miss rates with span attributes

7. **src/services/extractors/ceh_extractor.py**
   - @trace_async_method on fetch_metadata()
   - Add span attributes: identifier, format, response_time

8. **src/services/parsers/** (4 parser files)
   - @trace_method on parse() in each parser
   - Track parse duration and field extraction counts

9. **src/services/supporting_documents/supporting_doc_discoverer.py**
   - @trace_method on discover_from_*() methods
   - Track discovered URLs count

10. **src/services/supporting_documents/supporting_doc_downloader.py**
    - @trace_async_method on download()
    - @trace_async_method on download_batch()
    - Track download speed and file sizes

11. **src/services/document_extraction/document_extractor.py** & implementations
    - @trace_async_method on extract() in each extractor class
    - Track extraction duration per file type

### Tier 3: Repository Layer (MEDIUM)
Add light tracing for database operations:

12. **src/repositories/unit_of_work.py**
    - @trace_async_method on commit()
    - Track transaction duration

13. **src/repositories/*.py** (specific repositories)
    - @trace_method on insert/update operations
    - Track batch sizes for bulk operations

### Tier 4: Infrastructure (LOW)
Add observability for low-level operations:

14. **src/infrastructure/http_client.py**
    - @trace_async_method on HTTP calls
    - Track request/response times, status codes, bytes transferred

15. **src/infrastructure/database.py**
    - @trace_sync_method on create_tables()
    - Light tracing only (don't trace every query)

---

## PART 2: INTEGRATION SEQUENCE

### Phase 1: Foundation Setup (Do First)
1. Update src/config.py - add trace config
2. Update src/logging_config.py - add trace ID correlation
3. Update main.py - initialize/shutdown tracing
4. Run tests to ensure no breakage

### Phase 2: CLI Integration
5. Update src/cli.py - initialize/shutdown tracing
6. Test ETL CLI with --verbose flag

### Phase 3: Core Service Instrumentation
7. Add decorators to src/services/etl/etl_service.py (ALREADY STARTED)
8. Add decorators to metadata caching layer
9. Add decorators to extractors and parsers
10. Run full test suite

### Phase 4: Supporting Services
11. Add decorators to supporting doc discovery/download
12. Add decorators to document extraction
13. Add decorators to repositories

### Phase 5: Integration Testing
14. Create end-to-end test that validates trace output
15. Create performance test that validates span attributes
16. Test with Jaeger local instance (no docker)

---

## PART 3: TESTING STRATEGY

### Test Category 1: Unit Tests (Existing)
- No changes needed - continue running with pytest
- Decorators don't interfere with existing tests
- Mock tracing if needed in isolated tests

### Test Category 2: Integration Tests (New)
File: `tests/test_observability_integration.py`

```python
# Test that tracing is initialized
def test_tracing_initialized():
    from src.services.observability import get_tracer_provider
    provider = get_tracer_provider()
    assert provider is not None

# Test that decorators work
@pytest.mark.asyncio
async def test_trace_async_method_decorator():
    from src.services.observability import trace_async_method
    
    @trace_async_method()
    async def sample_function():
        return "result"
    
    result = await sample_function()
    assert result == "result"

# Test ETL pipeline creates spans
@pytest.mark.asyncio
async def test_etl_service_creates_spans(etl_service):
    # Mock span exporter to capture spans
    from opentelemetry.sdk.trace.export import InMemorySpanExporter
    
    # Run pipeline
    report = await etl_service.run_pipeline(limit=1)
    
    # Verify spans were created
    assert report['duration'] > 0
    # Verify cache stats captured
    assert 'metadata_cache_stats' in report
```

### Test Category 3: End-to-End Trace Validation (New)
File: `tests/test_trace_output.py`

```python
# Test that traces contain expected attributes
def test_etl_span_has_identifiers():
    # Run ETL with span exporter
    # Verify span contains identifier attribute
    # Verify span has start/end times
    # Verify span status is OK/ERROR as expected

# Test that trace hierarchy is correct
def test_trace_hierarchy():
    # Verify parent/child relationships
    # Pipeline > Extract > Batch > Fetch
    # Pipeline > Transform > Parse
    # Pipeline > Load

# Test that cache hits/misses are tracked
def test_cache_stats_in_spans():
    # Verify cache hit spans have event "cache_hit"
    # Verify cache miss spans have event "cache_miss"
    # Verify hit rate calculated correctly
```

### Test Category 4: Performance Monitoring (New)
File: `tests/test_trace_performance.py`

```python
# Test that span attributes are correctly set
def test_span_attributes_complete():
    # Verify identifier in span
    # Verify format in span
    # Verify status in span
    # Verify duration calculated

# Test that no information is lost
def test_trace_fidelity():
    # Run with limit=3
    # Verify 3 identifiers traced
    # Verify all phases traced
    # Verify no dropped spans
```

### Test Category 5: Error Handling with Traces (New)
File: `tests/test_trace_errors.py`

```python
# Test that exceptions are recorded in spans
@pytest.mark.asyncio
async def test_exception_recorded_in_span():
    # Simulate failure in metadata extraction
    # Verify exception recorded in span
    # Verify span status is ERROR
    # Verify error message in span

# Test that error recovery is traced
@pytest.mark.asyncio
async def test_retry_traced():
    # Simulate network error then success
    # Verify retry event added to span
    # Verify final status is OK
```

---

## PART 4: LOCAL TESTING WITHOUT DOCKER

### Option A: Test with In-Memory Exporter (RECOMMENDED)
```python
# In test setup
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, InMemorySpanExporter

exporter = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

# After running ETL
spans = exporter.get_finished_spans()
assert len(spans) > 0
assert spans[0].name == "run_pipeline"
```

### Option B: Test with File Export
```python
# Export spans to JSON file for inspection
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Even without Jaeger running, spans are queued
# They'll be sent when Jaeger becomes available
```

### Option C: Manual Local Jaeger (Optional)
If you want to run Jaeger locally without Docker:

```bash
# Download Jaeger binary
curl -L https://github.com/jaegertracing/jaeger/releases/download/v1.35.0/jaeger-v1.35.0-darwin-amd64.tar.gz | tar xz

# Run locally
./jaeger-v1.35.0-darwin-amd64/jaeger-agent

# View traces at http://localhost:16686
```

---

## PART 5: COMPREHENSIVE TEST PLAN SEQUENCE

### Week 1: Foundation
- [ ] Day 1: Update config.py, logging_config.py
- [ ] Day 2: Update main.py, test with `uv run python main.py`
- [ ] Day 3: Update cli.py, test with `uv run python -m src.cli etl --limit 3`
- [ ] Day 4: Run full test suite to verify no breakage
- [ ] Day 5: Create test_observability_integration.py

### Week 2: Service Instrumentation
- [ ] Day 1: Add decorators to etl_service.py
- [ ] Day 2: Add decorators to metadata_cache.py, extractors
- [ ] Day 3: Add decorators to parsers
- [ ] Day 4: Add decorators to supporting documents module
- [ ] Day 5: Run full test suite after each change

### Week 3: Testing & Validation
- [ ] Day 1: Create test_trace_output.py
- [ ] Day 2: Create test_trace_performance.py
- [ ] Day 3: Create test_trace_errors.py
- [ ] Day 4: Run end-to-end test with limit=10
- [ ] Day 5: Optimize and document

---

## PART 6: VERIFICATION CHECKLIST

After completing integration, verify:

### Tracing Initialization
- [ ] initialize_tracing() called in main.py startup
- [ ] initialize_tracing() called in cli.py etl command
- [ ] shutdown_tracing() called on shutdown
- [ ] No errors in logs about tracing initialization

### Span Creation
- [ ] ETL pipeline creates root span "run_pipeline"
- [ ] Extract phase creates child spans for batches
- [ ] Each batch fetch creates child spans
- [ ] Parse operations create spans
- [ ] Load operations create spans

### Span Attributes
- [ ] Identifier in spans where applicable
- [ ] Format (xml, json, rdf, schema_org) in metadata spans
- [ ] Duration calculated for all spans
- [ ] Status (OK/ERROR) set correctly

### Error Handling
- [ ] Exceptions recorded in spans
- [ ] Error descriptions included
- [ ] Retry events tracked
- [ ] Failed spans don't block pipeline

### Performance
- [ ] No significant slowdown from tracing
- [ ] Span overhead < 5% on ETL duration
- [ ] Memory usage stable (no leaks)
- [ ] Batch span processor working (not sending every span)

---

## PART 7: FILE-BY-FILE UPDATE GUIDE

Below is the exact sequence and changes needed for each file.

### Step 1: src/config.py
```python
# Add to imports
from src.services.observability import TraceConfig

# Add to Settings class
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Tracing Configuration
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    jaeger_enabled: bool = True
    jaeger_sample_rate: float = 1.0
```

### Step 2: src/logging_config.py
```python
# Update StructuredFormatter to include trace context
from opentelemetry import trace as otel_trace

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Get current span context
        span = otel_trace.get_current_span()
        trace_id = span.get_span_context().trace_id if span else "no-trace"
        
        # Include trace ID in log
        timestamp = ...
        log_message = (
            f"{timestamp} | {trace_id[:16]} | "
            f"{record.levelname:<8} | "
            ...
        )
```

### Step 3: main.py
```python
# Add to imports
from src.services.observability import initialize_tracing, shutdown_tracing, TraceConfig

# Update lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting tracing...")
    trace_config = TraceConfig(
        service_name=settings.app_name,
        jaeger_host=settings.jaeger_host,
        jaeger_port=settings.jaeger_port,
    )
    initialize_tracing(trace_config)
    logger.info("✓ Tracing initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down tracing...")
    shutdown_tracing()
    logger.info("✓ Tracing shutdown")
```

### Step 4: src/cli.py
```python
# Add to imports  
from src.services.observability import initialize_tracing, shutdown_tracing, TraceConfig

# Update etl command
@app.command()
async def etl(limit: Optional[int] = None, ...):
    # Initialize tracing
    trace_config = TraceConfig(
        service_name="dsh-etl-cli",
        environment="development"
    )
    initialize_tracing(trace_config)
    
    try:
        # Run pipeline
        service = ETLService(...)
        report = await service.run_pipeline(limit=limit)
    finally:
        # Shutdown tracing
        shutdown_tracing()
```

---

## PART 8: VALIDATION TESTS

Run after each phase:

```bash
# After Foundation Setup
uv run pytest tests/test_config.py -v
uv run python main.py  # Should initialize tracing without errors

# After CLI Integration
uv run python -m src.cli etl --limit 1
# Check output for "✓ Tracing initialized"

# After Service Instrumentation  
uv run pytest tests/ -v
# All tests should pass

# After Integration Testing
uv run pytest tests/test_observability_integration.py -v
uv run pytest tests/test_trace_output.py -v
uv run pytest tests/test_trace_performance.py -v
```

---

## PART 9: TROUBLESHOOTING DURING INTEGRATION

### Issue: "No module named opentelemetry"
Solution: `uv sync` to install dependencies

### Issue: "tracing not initialized" errors
Solution: Check that initialize_tracing() called before any traced function

### Issue: Spans missing attributes
Solution: Set attributes before span closes, use set_span_attributes()

### Issue: Tests failing with tracing
Solution: Mock tracing in tests that don't need it, or use InMemoryExporter

### Issue: Performance degradation
Solution: Reduce JAEGER_SAMPLE_RATE in .env to 0.1 or 0.01

---

## DELIVERABLES

After completing this plan, you will have:

✅ Distributed tracing throughout entire ETL system
✅ Automatic span creation for all major operations
✅ Trace correlation across services
✅ Performance metrics in spans
✅ Error tracking in spans
✅ Comprehensive test coverage
✅ Documentation for troubleshooting
✅ Local testing capability (no docker required)
✅ Foundation for future Jaeger integration

"""
