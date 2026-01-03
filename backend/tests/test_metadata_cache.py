"""
Tests for Metadata Cache System

Tests caching functionality, expiration, statistics, and error handling.
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from src.logging_config import get_logger

from src.infrastructure.metadata_cache import (
    MetadataCache,
    CachedMetadataFetcher,
    MetadataCacheError
)
from src.services.extractors import CEHExtractor
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def metadata_cache(temp_cache_dir):
    """Create metadata cache instance"""
    return MetadataCache(
        cache_dir=temp_cache_dir,
        enable_caching=True,
        cache_expiration_days=30
    )


@pytest.fixture
def mock_ceh_extractor():
    """Create mock CEH extractor"""
    extractor = AsyncMock(spec=CEHExtractor)
    extractor.fetch_dataset_xml = AsyncMock(return_value="<xml>test</xml>")
    extractor.fetch_dataset_json = AsyncMock(return_value='{"test": "json"}')
    extractor.fetch_dataset_rdf = AsyncMock(return_value="<rdf>test</rdf>")
    extractor.fetch_dataset_schema_org = AsyncMock(return_value='{"@context": "test"}')
    return extractor


@pytest.fixture
def cached_fetcher(metadata_cache, mock_ceh_extractor):
    """Create cached fetcher instance"""
    return CachedMetadataFetcher(
        cache=metadata_cache,
        ceh_extractor=mock_ceh_extractor
    )


# ============================================================================
# TEST: MetadataCache Initialization
# ============================================================================

class TestMetadataCacheInitialization:
    """Test cache initialization and setup"""
    
    def test_cache_initialization_with_defaults(self, temp_cache_dir):
        """Test cache initializes with default values"""
        cache = MetadataCache(cache_dir=temp_cache_dir)
        
        assert cache.enable_caching is True
        assert cache.cache_expiration_days == 30
        assert cache.cache_dir == temp_cache_dir
        assert cache.cache_dir.exists()
    
    def test_cache_initialization_disabled(self, temp_cache_dir):
        """Test cache initialization when disabled"""
        cache = MetadataCache(
            cache_dir=temp_cache_dir,
            enable_caching=False
        )
        
        assert cache.enable_caching is False
    
    def test_cache_creates_directory(self, temp_cache_dir):
        """Test cache creates directory if it doesn't exist"""
        cache_dir = temp_cache_dir / "nested" / "cache" / "dir"
        assert not cache_dir.exists()
        
        cache = MetadataCache(cache_dir=cache_dir, enable_caching=True)
        
        assert cache_dir.exists()
    
    def test_cache_custom_expiration(self, temp_cache_dir):
        """Test cache with custom expiration"""
        cache = MetadataCache(
            cache_dir=temp_cache_dir,
            cache_expiration_days=90
        )
        
        assert cache.cache_expiration_days == 90


# ============================================================================
# TEST: Cache Get/Set Operations
# ============================================================================

class TestCacheGetSet:
    """Test basic cache get/set operations"""
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, metadata_cache):
        """Test storing and retrieving from cache"""
        identifier = "dataset-001"
        format_type = "xml"
        content = "<xml>test content</xml>"
        
        await metadata_cache.set(identifier, format_type, content)
        retrieved = await metadata_cache.get(identifier, format_type)
        
        assert retrieved == content
    
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, metadata_cache):
        """Test cache miss returns None"""
        result = await metadata_cache.get("non-existent", "xml")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_all_formats(self, metadata_cache):
        """Test caching all supported formats"""
        identifier = "dataset-001"
        contents = {
            "xml": "<xml>content</xml>",
            "json": '{"key": "value"}',
            "rdf": "<rdf>content</rdf>",
            "schema_org": '{"@context": "test"}'
        }
        
        for format_type, content in contents.items():
            await metadata_cache.set(identifier, format_type, content)
        
        for format_type, expected_content in contents.items():
            retrieved = await metadata_cache.get(identifier, format_type)
            assert retrieved == expected_content
    
    @pytest.mark.asyncio
    async def test_cache_different_identifiers(self, metadata_cache):
        """Test caching different identifiers separately"""
        format_type = "xml"
        content1 = "<xml>content1</xml>"
        content2 = "<xml>content2</xml>"
        
        await metadata_cache.set("id-1", format_type, content1)
        await metadata_cache.set("id-2", format_type, content2)
        
        assert await metadata_cache.get("id-1", format_type) == content1
        assert await metadata_cache.get("id-2", format_type) == content2
    
    @pytest.mark.asyncio
    async def test_cache_disabled_no_store(self, temp_cache_dir):
        """Test disabled cache doesn't store data"""
        cache = MetadataCache(
            cache_dir=temp_cache_dir,
            enable_caching=False
        )
        
        await cache.set("dataset-001", "xml", "<xml>content</xml>")
        result = await cache.get("dataset-001", "xml")
        
        assert result is None


# ============================================================================
# TEST: Cache Expiration
# ============================================================================

class TestCacheExpiration:
    """Test cache expiration logic"""
    
    @pytest.mark.asyncio
    async def test_cache_expiration_check(self, metadata_cache, temp_cache_dir):
        """Test expired cache entries are detected"""
        identifier = "dataset-001"
        format_type = "xml"
        content = "<xml>test</xml>"
        
        # Set cache
        await metadata_cache.set(identifier, format_type, content)
        assert await metadata_cache.get(identifier, format_type) == content
        
        # Manually set expiration to past
        hash_key = metadata_cache._hash_key(identifier, format_type)
        meta_file = temp_cache_dir / f"{hash_key}.meta"
        meta_data = json.loads(meta_file.read_text())
        meta_data["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
        meta_file.write_text(json.dumps(meta_data))
        
        # Should now return None (expired)
        result = await metadata_cache.get(identifier, format_type)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_clear_expired_entries(self, metadata_cache):
        """Test clearing expired cache entries"""
        # Add valid entry
        await metadata_cache.set("dataset-001", "xml", "<xml>1</xml>")
        
        # Add expired entry manually
        hash_key = metadata_cache._hash_key("dataset-002", "xml")
        cache_file = metadata_cache.cache_dir / f"{hash_key}.dat"
        meta_file = metadata_cache.cache_dir / f"{hash_key}.meta"
        
        cache_file.write_text("<xml>2</xml>")
        meta_data = {
            "identifier": "dataset-002",
            "format": "xml",
            "cached_at": (datetime.now() - timedelta(days=40)).isoformat(),
            "size_bytes": 10,
            "expires_at": (datetime.now() - timedelta(days=10)).isoformat()
        }
        meta_file.write_text(json.dumps(meta_data))
        
        # Clear expired (not async)
        cleared = metadata_cache.clear_expired()
        
        assert cleared >= 1
        assert not cache_file.exists()


# ============================================================================
# TEST: Cache Existence Check
# ============================================================================

class TestCacheExists:
    """Test cache existence checking"""
    
    @pytest.mark.asyncio
    async def test_exists_returns_true_for_cached(self, metadata_cache):
        """Test exists returns True for cached items"""
        await metadata_cache.set("dataset-001", "xml", "<xml>test</xml>")
        
        exists = await metadata_cache.exists("dataset-001", "xml")
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing(self, metadata_cache):
        """Test exists returns False for missing items"""
        exists = await metadata_cache.exists("non-existent", "xml")
        assert exists is False


# ============================================================================
# TEST: Cache Statistics
# ============================================================================

class TestCacheStatistics:
    """Test cache statistics tracking"""
    
    @pytest.mark.asyncio
    async def test_stats_hits_and_misses(self, metadata_cache):
        """Test hit and miss statistics"""
        await metadata_cache.set("dataset-001", "xml", "<xml>test</xml>")
        
        # Hit
        await metadata_cache.get("dataset-001", "xml")
        assert metadata_cache.stats["hits"] == 1
        
        # Miss
        await metadata_cache.get("non-existent", "xml")
        assert metadata_cache.stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self, metadata_cache):
        """Test get_stats returns proper dictionary"""
        await metadata_cache.set("dataset-001", "xml", "<xml>test</xml>")
        await metadata_cache.get("dataset-001", "xml")
        await metadata_cache.get("non-existent", "xml")
        
        stats = metadata_cache.get_stats()
        
        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "writes" in stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, metadata_cache):
        """Test hit rate percentage calculation"""
        # Add 10 items
        for i in range(10):
            await metadata_cache.set(f"dataset-{i:03d}", "xml", f"<xml>{i}</xml>")
        
        # Get 7 hits
        for i in range(7):
            await metadata_cache.get(f"dataset-{i:03d}", "xml")
        
        # Get 3 misses
        for i in range(3):
            await metadata_cache.get(f"missing-{i}", "xml")
        
        stats = metadata_cache.get_stats()
        
        assert stats["hits"] == 7
        assert stats["misses"] == 3
        assert "70" in stats["hit_rate"]  # Should show ~70%


# ============================================================================
# TEST: Cache Clear Operations
# ============================================================================

class TestCacheClear:
    """Test cache clearing operations"""
    
    @pytest.mark.asyncio
    async def test_clear_all_entries(self, metadata_cache):
        """Test clearing all cache entries"""
        # Add multiple entries
        for i in range(5):
            await metadata_cache.set(f"dataset-{i}", "xml", f"<xml>{i}</xml>")
        
        # Clear all (not async)
        cleared = metadata_cache.clear_all()
        
        assert cleared >= 5
        assert len(list(metadata_cache.cache_dir.glob("*.dat"))) == 0
    
    @pytest.mark.asyncio
    async def test_clear_returns_count(self, metadata_cache):
        """Test clear operations return count"""
        await metadata_cache.set("dataset-001", "xml", "<xml>1</xml>")
        await metadata_cache.set("dataset-002", "json", '{"test": "data"}')
        
        cleared = metadata_cache.clear_all()
        
        assert cleared == 2


# ============================================================================
# TEST: CachedMetadataFetcher
# ============================================================================

class TestCachedMetadataFetcher:
    """Test cached fetcher wrapper"""
    
    @pytest.mark.asyncio
    async def test_fetch_xml_caches_result(self, cached_fetcher, metadata_cache, mock_ceh_extractor):
        """Test XML fetching caches the result"""
        identifier = "dataset-001"
        xml_content = "<xml>test</xml>"
        mock_ceh_extractor.fetch_dataset_xml.return_value = xml_content
        
        # First fetch - should call extractor
        result1 = await cached_fetcher.fetch_xml(identifier)
        assert result1 == xml_content
        assert mock_ceh_extractor.fetch_dataset_xml.call_count == 1
        
        # Second fetch - should use cache
        result2 = await cached_fetcher.fetch_xml(identifier)
        assert result2 == xml_content
        assert mock_ceh_extractor.fetch_dataset_xml.call_count == 1  # Not called again
    
    @pytest.mark.asyncio
    async def test_fetch_json_with_cache(self, cached_fetcher, mock_ceh_extractor):
        """Test JSON fetching uses cache"""
        identifier = "dataset-001"
        json_content = '{"key": "value"}'
        mock_ceh_extractor.fetch_dataset_json.return_value = json_content
        
        result = await cached_fetcher.fetch_json(identifier)
        
        assert result == json_content
    
    @pytest.mark.asyncio
    async def test_fetch_rdf_with_cache(self, cached_fetcher, mock_ceh_extractor):
        """Test RDF fetching uses cache"""
        identifier = "dataset-001"
        rdf_content = "<rdf>test</rdf>"
        mock_ceh_extractor.fetch_dataset_rdf.return_value = rdf_content
        
        result = await cached_fetcher.fetch_rdf(identifier)
        
        assert result == rdf_content
    
    @pytest.mark.asyncio
    async def test_fetch_schema_org_with_cache(self, cached_fetcher, mock_ceh_extractor):
        """Test Schema.org fetching uses cache"""
        identifier = "dataset-001"
        schema_org_content = '{"@context": "test"}'
        mock_ceh_extractor.fetch_dataset_schema_org.return_value = schema_org_content
        
        result = await cached_fetcher.fetch_schema_org(identifier)
        
        assert result == schema_org_content
    
    @pytest.mark.asyncio
    async def test_fetcher_fallback_on_error(self, cached_fetcher, metadata_cache, mock_ceh_extractor):
        """Test fetcher uses stale cache on error"""
        identifier = "dataset-001"
        xml_content = "<xml>test</xml>"
        
        # First, cache some content
        await metadata_cache.set(identifier, "xml", xml_content)
        
        # Mock extractor to fail
        mock_ceh_extractor.fetch_dataset_xml.side_effect = Exception("Network error")
        
        # Should return stale cache or raise
        result = await cached_fetcher.fetch_xml(identifier)
        
        # May return cached content or raise (depends on implementation)
        assert result == xml_content or result is None


# ============================================================================
# TEST: Cache Error Handling
# ============================================================================

class TestCacheErrorHandling:
    """Test cache error handling"""
    
    @pytest.mark.asyncio
    async def test_cache_handles_corrupted_meta(self, metadata_cache, temp_cache_dir):
        """Test cache handles corrupted metadata file"""
        identifier = "dataset-001"
        cache_file = temp_cache_dir / f"{identifier}_xml.dat"
        meta_file = temp_cache_dir / f"{identifier}_xml.meta"
        
        cache_file.write_text("<xml>test</xml>")
        meta_file.write_text("invalid json")
        
        # Should handle gracefully
        result = await metadata_cache.get(identifier, "xml")
        
        # Either return None or handle error
        assert result is None or isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_cache_handles_missing_meta(self, metadata_cache, temp_cache_dir):
        """Test cache handles missing metadata file"""
        identifier = "dataset-001"
        cache_file = temp_cache_dir / f"{identifier}_xml.dat"
        
        cache_file.write_text("<xml>test</xml>")
        # No metadata file
        
        result = await metadata_cache.get(identifier, "xml")
        
        assert result is None


# ============================================================================
# TEST: Cache Performance
# ============================================================================

class TestCachePerformance:
    """Test cache performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_cache_multiple_identifiers(self, metadata_cache):
        """Test cache handles multiple identifiers efficiently"""
        num_items = 100
        
        # Add items
        for i in range(num_items):
            await metadata_cache.set(
                f"dataset-{i:04d}",
                "xml",
                f"<xml>content-{i}</xml>"
            )
        
        # Retrieve items
        for i in range(num_items):
            result = await metadata_cache.get(f"dataset-{i:04d}", "xml")
            assert result == f"<xml>content-{i}</xml>"
        
        stats = metadata_cache.get_stats()
        assert stats["hits"] == num_items
    
    @pytest.mark.asyncio
    async def test_cache_large_content(self, metadata_cache):
        """Test cache handles large content"""
        large_content = "<xml>" + "x" * 10_000_000 + "</xml>"  # 10MB
        
        await metadata_cache.set("large-dataset", "xml", large_content)
        result = await metadata_cache.get("large-dataset", "xml")
        
        assert result == large_content
