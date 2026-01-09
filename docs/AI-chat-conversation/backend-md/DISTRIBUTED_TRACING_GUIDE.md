"""
DISTRIBUTED TRACING INTEGRATION GUIDE
=====================================

This guide explains how to integrate OpenTelemetry distributed tracing into your ETL pipeline
and other services for comprehensive observability across your system.

## Quick Start

### 1. Initialize Tracing in your main application

In main.py or cli.py:

```python
from src.services.observability import initialize_tracing, TraceConfig, shutdown_tracing
from src.config import settings

# Initialize tracing at application startup
trace_config = TraceConfig(
    service_name="dsh-etl-search-ai",
    jaeger_host=os.getenv("JAEGER_HOST", "localhost"),
    jaeger_port=int(os.getenv("JAEGER_PORT", "6831")),
    environment=settings.app_env
)
initialize_tracing(trace_config)

# Your application code...

# Shutdown at application exit
shutdown_tracing()
```

### 2. Add Decorators to Services

#### Option A: Async Methods (Recommended)

```python
from src.services.observability import trace_async_method

class ETLService:
    @trace_async_method(attributes={"service": "etl", "phase": "extract"})
    async def fetch_metadata(self, identifier: str):
        # Method body - spans are automatically created
        return metadata
```

#### Option B: Sync Methods

```python
from src.services.observability import trace_method

class MetadataParser:
    @trace_method()
    def parse_iso19139(self, content: str):
        # Method body
        return parsed_data
```

#### Option C: Manual Span Creation

```python
from src.services.observability import with_span, set_span_attributes, add_span_event

async def process_batch(identifiers):
    with with_span("process_batch", {"batch_size": len(identifiers)}) as span:
        for identifier in identifiers:
            add_span_event(span, "processing_identifier", {"id": identifier})
            # Do work
            add_span_event(span, "identifier_processed", {"id": identifier})
```

### 3. Set Jaeger Exporter Environment Variables

Create/update .env:

```
# Jaeger Configuration
JAEGER_HOST=localhost          # Jaeger agent host (default: localhost)
JAEGER_PORT=6831              # Jaeger agent port (default: 6831)
JAEGER_ENABLED=true           # Enable/disable tracing (default: true)
JAEGER_SAMPLER=const          # Sampling strategy (const, probabilistic, etc)
JAEGER_SAMPLER_PARAM=1.0      # Sample rate 0.0-1.0 (1.0 = 100%)
```

### 4. Start Jaeger Locally (for development)

```bash
# Using Docker
docker run -d \
  --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 6831:6831/udp \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Then view UI: http://localhost:16686
```

### 5. Install Required Package

```bash
cd backend
uv pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Your Application                            │
│  (ETLService, Parsers, Extractors, etc)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─ @trace_async_method decorator
                 ├─ @trace_method decorator  
                 └─ with_span() context manager
                 │
┌────────────────▼────────────────────────────────────────────┐
│          OpenTelemetry SDK (tracing_config.py)              │
│  - Tracer Provider                                           │
│  - Span Processors (batching, export)                       │
│  - Resource (service name, version, environment)           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─ Jaeger Exporter (UDP)
                 └─ Prometheus Metrics (optional)
                 │
        ┌────────▼──────────┐
        │  Jaeger Agent     │  (localhost:6831)
        │  (local)          │
        └────────┬──────────┘
                 │
        ┌────────▼────────────────┐
        │  Jaeger Collector       │
        │  (aggregates traces)    │
        └────────┬────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  Jaeger UI                │
        │  (http://localhost:16686) │
        │                           │
        │  - Trace Timeline         │
        │  - Service Dependencies   │
        │  - Performance Analysis   │
        └───────────────────────────┘
```

---

## Key Features

### 1. Automatic Span Creation

Decorators automatically create spans with:
- Operation name (function/method name)
- Start/end times
- Duration calculation
- Exception recording
- Status (OK/ERROR)

### 2. Context Propagation

Spans maintain hierarchy:
```
Pipeline Execution
├── Extract Phase
│   ├── Batch 1
│   │   ├── Fetch XML
│   │   ├── Fetch JSON
│   │   ├── Fetch RDF
│   │   └── Fetch Schema.org
│   └── Batch 2
├── Transform Phase
│   ├── Parse ISO19139
│   ├── Parse JSON
│   └── Parse RDF
└── Load Phase
    └── Store in Database
```

### 3. Custom Attributes

Add context to spans:

```python
span.set_attribute("identifier", "be0bdc0e-bc2e-4f1d")
span.set_attribute("format", "xml")
span.set_attribute("file_size_kb", 256)
```

### 4. Events

Track important moments:

```python
add_span_event(span, "cache_hit")
add_span_event(span, "download_started", {"url": "https://..."})
add_span_event(span, "parsing_completed", {"records": 42})
```

---

## Integration Checklist

### Phase 1: Core ETL Service
- [ ] Import observability module in etl_service.py
- [ ] Add @trace_async_method to run_pipeline()
- [ ] Add span attributes for batch_size, concurrency
- [ ] Add events for phase transitions

### Phase 2: Metadata Extraction
- [ ] Add tracing to _fetch_metadata_for_identifier()
- [ ] Add span attributes for identifier, format
- [ ] Track cache hits/misses
- [ ] Track network latency

### Phase 3: Parsing
- [ ] Add @trace_method to ISO19139Parser.parse()
- [ ] Add @trace_method to JSONMetadataParser.parse()
- [ ] Add @trace_method to RDFParser.parse()
- [ ] Add @trace_method to SchemaOrgParser.parse()
- [ ] Track parse duration per format

### Phase 4: Document Processing
- [ ] Add tracing to SupportingDocDiscoverer.discover()
- [ ] Add tracing to SupportingDocDownloader.download()
- [ ] Add tracing to UniversalDocumentExtractor.extract()
- [ ] Track download speeds

### Phase 5: Database Loading
- [ ] Add tracing to repository insert/update operations
- [ ] Track transaction durations
- [ ] Track bulk insert performance

---

## Usage Examples

### Example 1: Trace Async Function

```python
from src.services.observability import trace_async_function

@trace_async_function(attributes={"service": "parser"})
async def parse_metadata(content: str, format: str) -> Dataset:
    # Automatically traced!
    parser = get_parser(format)
    return await parser.parse(content)
```

### Example 2: Trace with Custom Span

```python
from src.services.observability import with_span, add_span_event

async def process_batch(identifiers: list):
    with with_span("process_batch") as span:
        span.set_attribute("batch_size", len(identifiers))
        
        for identifier in identifiers:
            add_span_event(span, "start_processing", {"id": identifier})
            result = await process_identifier(identifier)
            add_span_event(span, "complete_processing", {
                "id": identifier,
                "status": "success" if result else "failed"
            })
```

### Example 3: Exception Handling

```python
from src.services.observability import record_exception

async def fetch_metadata(identifier):
    span = get_current_span()
    try:
        return await ceh_api.fetch(identifier)
    except IOError as e:
        record_exception(span, e, {
            "identifier": identifier,
            "retry_count": 3
        })
        raise
```

### Example 4: Performance Monitoring

```python
import time
from src.services.observability import with_span

async def download_file(url: str):
    with with_span("download_file", {"url": url}) as span:
        start = time.time()
        
        # Download logic
        downloaded = await http_client.get(url)
        
        duration = time.time() - start
        span.set_attribute("duration_ms", int(duration * 1000))
        span.set_attribute("size_bytes", len(downloaded))
        span.set_attribute("speed_mbps", (len(downloaded) / duration / 1_000_000))
```

---

## Jaeger UI Navigation

### 1. Service Selection
- Dropdown: Select "dsh-etl-search-ai" service
- Shows all traces for this service

### 2. View Trace Timeline
- Click trace to see execution flow
- Hover spans for duration
- Click span to see attributes

### 3. Service Dependencies
- Shows how services call each other
- "Service Graph" tab
- Visualize system architecture

### 4. Performance Analysis
- Filter by duration (slow traces)
- Find bottlenecks
- Compare operation durations

---

## Performance Tips

### 1. Sampling for Production

```python
# Only sample 10% of traces in production
trace_config = TraceConfig(
    sample_rate=0.1 if settings.app_env == "production" else 1.0
)
```

### 2. Batch Span Processor

Spans are automatically batched:
- Default: sends every 2048 spans or 5 seconds
- Reduces network overhead

### 3. Memory Management

```python
# Force flush periodically
from src.services.observability import get_tracer_provider

if i % 100 == 0:  # Every 100 iterations
    get_tracer_provider().force_flush()
```

---

## Troubleshooting

### Problem: No traces appearing in Jaeger

1. Check Jaeger is running:
   ```bash
   docker ps | grep jaeger
   ```

2. Verify network connectivity:
   ```bash
   telnet localhost 6831
   ```

3. Check initialization was called:
   ```python
   from src.services.observability import initialize_tracing
   initialize_tracing()  # Must be called before any tracing
   ```

### Problem: Spans missing attributes

- Attributes must be set before span closes
- Use `set_span_attributes()` instead of manual assignment
- Check attribute types (str, int, float, bool only)

### Problem: Performance impact

- Use sampling: `trace_config.sample_rate = 0.1`
- Reduce batch span processor interval
- Filter noisy spans (disable for low-level operations)

---

## Next Steps

1. Update requirements.txt:
   ```bash
   opentelemetry-api==1.21.0
   opentelemetry-sdk==1.21.0
   opentelemetry-exporter-jaeger==1.21.0
   opentelemetry-exporter-prometheus==0.42b0
   ```

2. Initialize tracing in main.py

3. Add decorators to key services (Phase 1 above)

4. Test with Jaeger UI: http://localhost:16686

5. Monitor and optimize based on trace data

---

## References

- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- Jaeger Documentation: https://www.jaegertracing.io/docs/
- Spans & Traces: https://opentelemetry.io/docs/concepts/signals/traces/
"""
