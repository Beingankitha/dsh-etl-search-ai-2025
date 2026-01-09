# Metadata Cache System - Implementation Guide

## Overview

The **MetadataCache** system provides intelligent caching for metadata documents (XML, JSON, RDF, Schema.org) fetched from the CEH API, significantly improving ETL pipeline performance by avoiding re-downloads.

## Architecture

```
ETL Pipeline
    ↓
CachedMetadataFetcher (wrapper)
    ├→ MetadataCache (check cache)
    │   ├→ Cache hit: return cached content
    │   └→ Cache miss: fetch fresh data
    └→ CEHExtractor (actual fetch)

Cache Storage:
data/metadata_cache/
├── {hash}.dat      (actual content)
└── {hash}.meta     (metadata: timestamp, size, expiration)
```

## Key Features

1. **Automatic Caching**: Content is automatically cached when fetched
2. **Cache Expiration**: Configurable TTL (default: 30 days)
3. **Multi-Format Support**: XML, JSON, RDF, Schema.org
4. **Statistics Tracking**: Hit rate, miss rate, write count
5. **Expired Entry Cleanup**: Automatic removal of stale cache
6. **Fallback Support**: Uses stale cache if fetch fails
7. **Thread-Safe**: Safe for concurrent operations

## Usage in ETL Service

### Basic Setup

```python
from pathlib import Path
from src.services.etl import (
    ETLService, 
    MetadataCache,
    CachedMetadataFetcher
)

# Initialize cache
metadata_cache = MetadataCache(
    cache_dir=Path("./data/metadata_cache"),
    enable_caching=True,
    cache_expiration_days=30
)

# Wrap CEH extractor with caching
cached_fetcher = CachedMetadataFetcher(
    cache=metadata_cache,
    ceh_extractor=etl_service.ceh_extractor
)

# Use in pipeline
xml_content = await cached_fetcher.fetch_xml("dataset-123")
json_content = await cached_fetcher.fetch_json("dataset-123")
rdf_content = await cached_fetcher.fetch_rdf("dataset-123")
schema_org_content = await cached_fetcher.fetch_schema_org("dataset-123")
```

### Integration with ETL Service

```python
# In ETLService.__init__():
self.metadata_cache = MetadataCache(
    cache_dir=cache_dir,
    enable_caching=True,
    cache_expiration_days=30
)

self.cached_fetcher = CachedMetadataFetcher(
    cache=self.metadata_cache,
    ceh_extractor=self.ceh_extractor
)

# In metadata extraction phase:
async def _extract_metadata(self, identifier: str):
    """Extract metadata with caching"""
    metadata_docs = {
        'xml': await self.cached_fetcher.fetch_xml(identifier),
        'json': await self.cached_fetcher.fetch_json(identifier),
        'rdf': await self.cached_fetcher.fetch_rdf(identifier),
        'schema_org': await self.cached_fetcher.fetch_schema_org(identifier),
    }
    return metadata_docs
```

## Cache Statistics

```python
# Get cache statistics
stats = metadata_cache.get_stats()
print(stats)

# Output:
{
    "hits": 245,
    "misses": 55,
    "hit_rate": "81.7%",
    "writes": 55,
    "expired": 0,
    "errors": 2,
    "cache_dir": "./data/metadata_cache",
    "entries": 55
}
```

## Cache Management

### Clear Expired Entries
```python
# Remove entries older than cache_expiration_days
cleared = metadata_cache.clear_expired()
print(f"Cleared {cleared} expired entries")
```

### Clear All Cache
```python
# Remove all cached data
cleared = metadata_cache.clear_all()
print(f"Cleared {cleared} entries")
```

### Check Cache Status
```python
# Check if entry exists in cache
exists = await metadata_cache.exists("dataset-123", "xml")
if exists:
    print("XML for dataset-123 is in cache")
else:
    print("XML for dataset-123 not in cache")
```

## Performance Benefits

### Example: Processing 1000 datasets

**Without Cache:**
- 4000 API calls (1000 × 4 formats)
- ~40 seconds (10ms per call, 5 concurrent)
- High API load on CEH server

**With Cache (first run):**
- 4000 API calls (all cache misses)
- ~40 seconds (same as above)
- Metadata cached for future runs

**With Cache (subsequent runs):**
- 0 API calls (100% cache hit)
- ~5 seconds (only parser processing)
- **8x faster pipeline**
- Minimal API load

## Configuration

### Disable Caching
```python
metadata_cache = MetadataCache(
    enable_caching=False  # Bypass cache entirely
)
```

### Adjust Cache Expiration
```python
# Keep cache for 90 days
metadata_cache = MetadataCache(
    cache_expiration_days=90
)

# Short cache (1 day for testing)
metadata_cache = MetadataCache(
    cache_expiration_days=1
)
```

### Custom Cache Directory
```python
metadata_cache = MetadataCache(
    cache_dir=Path("/mnt/fast_storage/metadata_cache")
)
```

## Cache File Structure

```
data/metadata_cache/
├── a1b2c3d4e5f6g7h8.dat       # XML content for dataset-123
├── a1b2c3d4e5f6g7h8.meta      # XML metadata
├── i9j0k1l2m3n4o5p6.dat       # JSON content for dataset-124
├── i9j0k1l2m3n4o5p6.meta      # JSON metadata
├── q7r8s9t0u1v2w3x4.dat       # RDF content for dataset-125
├── q7r8s9t0u1v2w3x4.meta      # RDF metadata
└── ...
```

### Metadata File Example (a1b2c3d4e5f6g7h8.meta)
```json
{
  "identifier": "dataset-123",
  "format": "xml",
  "cached_at": "2026-01-03T14:32:15.123456",
  "size_bytes": 2847,
  "expires_at": "2026-02-02T14:32:15.123456"
}
```

## Error Handling

### Fetch Failure with Cache Fallback
```python
# If API call fails but cache exists, use stale cache
try:
    content = await cached_fetcher.fetch_xml("dataset-123")
    # If network error occurs, stale cache is returned
    # Pipeline continues with cached data
except:
    # No cache available, error propagates
    logger.error("Failed to fetch and no cache available")
```

### Cache Statistics on Error
```python
stats = metadata_cache.get_stats()
if stats["errors"] > 0:
    logger.warning(f"Cache errors: {stats['errors']}")
```

## Testing the Cache

```python
import asyncio
from src.services.etl import MetadataCache, CachedMetadataFetcher

async def test_cache():
    # Create cache
    cache = MetadataCache(cache_dir=Path("./test_cache"))
    
    # First fetch - cache miss
    content1 = await cache.get("id-1", "xml")
    assert content1 is None
    
    # Store in cache
    await cache.set("id-1", "xml", "<xml>test</xml>")
    
    # Second fetch - cache hit
    content2 = await cache.get("id-1", "xml")
    assert content2 == "<xml>test</xml>"
    
    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    
    # Cleanup
    cache.clear_all()

# Run test
asyncio.run(test_cache())
```

## Monitoring & Debugging

### Enable Debug Logging
```python
import logging
logging.getLogger("src.services.etl.metadata_cache").setLevel(logging.DEBUG)

# Now you'll see:
# DEBUG: Cache miss: dataset-123/xml
# DEBUG: Cached: dataset-123/xml (2847 bytes)
# DEBUG: Cache hit: dataset-123/xml
```

### Pipeline Reporting
```python
# After ETL pipeline runs, check cache stats
report = etl_service.report
print(f"Cache hit rate: {report['cache_stats']['hit_rate']}")
print(f"Cache entries: {report['cache_stats']['entries']}")
```

## Best Practices

1. **Enable by Default**: Cache is beneficial for all scenarios
2. **Clear Periodically**: Run `clear_expired()` weekly to manage disk space
3. **Monitor Hit Rate**: Track cache effectiveness via statistics
4. **Adjust TTL**: Use longer TTL for stable datasets, shorter for rapidly changing ones
5. **Separate Cache Dir**: Use fast storage (SSD) for cache directory
6. **Backup Cache**: Cache can be cleared anytime, data regenerates if needed

## Troubleshooting

### Cache Not Working
```python
# Check if caching is enabled
if not metadata_cache.enable_caching:
    print("Caching is disabled!")

# Check cache directory permissions
metadata_cache.cache_dir.mkdir(parents=True, exist_ok=True)
```

### Low Hit Rate
```python
stats = metadata_cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}")  # Should be > 80% on repeat runs

# If low:
# 1. Check cache_expiration_days (may be too short)
# 2. Check if cache_dir has enough disk space
# 3. Check error count in stats
```

### Disk Space Issues
```python
# Clear old cache entries
cleared = metadata_cache.clear_expired()
print(f"Cleared {cleared} expired entries")

# If still too large, reduce TTL or clear all
metadata_cache.clear_all()
```
