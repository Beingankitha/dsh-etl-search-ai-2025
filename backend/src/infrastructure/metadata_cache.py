"""
Metadata Cache System for ETL Pipeline

Provides caching for downloaded metadata files (XML, JSON, RDF, Schema.org)
to avoid re-downloading and improve pipeline performance.

Features:
- File-based caching with hash-based filenames
- Support for multiple metadata formats
- Cache statistics and hit/miss tracking
- Configurable cache expiration
- Thread-safe operations
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from src.logging_config import get_logger

logger = get_logger(__name__)


class MetadataCacheError(Exception):
    """Exception for cache operations."""
    pass


class MetadataCache:
    """
    Cache system for downloaded metadata documents.
    
    Stores metadata by identifier and format:
    cache_dir/
    ├── {identifier}_{format}.dat    (actual content)
    └── {identifier}_{format}.meta   (metadata: timestamp, size, etc)
    """

    SUPPORTED_FORMATS = ["xml", "json", "rdf", "schema_org"]
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        enable_caching: bool = True,
        cache_expiration_days: int = 30,
    ):
        """
        Initialize metadata cache.

        Args:
            cache_dir: Directory for cache storage
            enable_caching: Enable/disable caching
            cache_expiration_days: Days before cached items expire
        """
        self.enable_caching = enable_caching
        self.cache_expiration_days = cache_expiration_days
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./data/metadata_cache")
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "expired": 0,
            "errors": 0,
            "hits_by_format": {fmt: 0 for fmt in self.SUPPORTED_FORMATS},
            "misses_by_format": {fmt: 0 for fmt in self.SUPPORTED_FORMATS},
            "supporting_docs_misses": 0,  # Track supporting doc download misses
        }
        
        if enable_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Metadata cache initialized: {self.cache_dir}")

    async def get(self, identifier: str, format: str) -> Optional[str]:
        """
        Get cached metadata.

        Args:
            identifier: Dataset identifier
            format: Metadata format (xml, json, rdf, schema_org)

        Returns:
            Cached content, or None if not found/expired
        """
        if not self.enable_caching:
            self.stats["misses"] += 1
            if format in self.stats["misses_by_format"]:
                self.stats["misses_by_format"][format] += 1
            return None

        try:
            cache_file = self._get_cache_path(identifier, format)
            meta_file = self._get_meta_path(identifier, format)

            # Check if cache files exist
            if not cache_file.exists() or not meta_file.exists():
                self.stats["misses"] += 1
                if format in self.stats["misses_by_format"]:
                    self.stats["misses_by_format"][format] += 1
                logger.debug(f"Cache miss: {identifier}/{format}")
                return None

            # Check expiration
            if self._is_expired(meta_file):
                logger.debug(f"Cache expired: {identifier}/{format}")
                self._cleanup_cache(identifier, format)
                self.stats["expired"] += 1
                self.stats["misses"] += 1
                if format in self.stats["misses_by_format"]:
                    self.stats["misses_by_format"][format] += 1
                return None

            # Read and return cached content
            content = cache_file.read_text(encoding="utf-8")
            self.stats["hits"] += 1
            if format in self.stats["hits_by_format"]:
                self.stats["hits_by_format"][format] += 1
            logger.debug(f"Cache hit: {identifier}/{format}")
            return content

        except Exception as e:
            logger.error(f"Cache read error for {identifier}/{format}: {e}")
            self.stats["errors"] += 1
            self.stats["misses"] += 1
            if format in self.stats["misses_by_format"]:
                self.stats["misses_by_format"][format] += 1
            return None

    async def set(
        self,
        identifier: str,
        format: str,
        content: str,
    ) -> bool:
        """
        Cache metadata content.

        Args:
            identifier: Dataset identifier
            format: Metadata format
            content: Metadata content to cache

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enable_caching:
            return False

        try:
            cache_file = self._get_cache_path(identifier, format)
            meta_file = self._get_meta_path(identifier, format)

            # Write content
            cache_file.write_text(content, encoding="utf-8")

            # Write metadata
            metadata = {
                "identifier": identifier,
                "format": format,
                "cached_at": datetime.now().isoformat(),
                "size_bytes": len(content),
                "expires_at": (
                    datetime.now() + timedelta(days=self.cache_expiration_days)
                ).isoformat(),
            }
            meta_file.write_text(json.dumps(metadata, indent=2))

            self.stats["writes"] += 1
            logger.debug(f"Cached: {identifier}/{format} ({len(content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Cache write error for {identifier}/{format}: {e}")
            self.stats["errors"] += 1
            return False

    async def exists(self, identifier: str, format: str) -> bool:
        """Check if valid cache entry exists."""
        if not self.enable_caching:
            return False

        cache_file = self._get_cache_path(identifier, format)
        meta_file = self._get_meta_path(identifier, format)

        if not cache_file.exists() or not meta_file.exists():
            return False

        return not self._is_expired(meta_file)

    def clear_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of cleared entries
        """
        cleared = 0
        try:
            for meta_file in self.cache_dir.glob("*.meta"):
                if self._is_expired(meta_file):
                    # Get corresponding cache file
                    cache_file = meta_file.with_suffix(".dat")
                    cache_file.unlink(missing_ok=True)
                    meta_file.unlink(missing_ok=True)
                    cleared += 1
                    logger.debug(f"Cleared expired cache: {meta_file.stem}")
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")

        return cleared

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of cleared entries
        """
        cleared = 0
        try:
            for cache_file in self.cache_dir.glob("*.dat"):
                cache_file.unlink()
                meta_file = cache_file.with_suffix(".meta")
                meta_file.unlink(missing_ok=True)
                cleared += 1
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

        return cleared

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        # Calculate hit rate by format
        hits_by_format = {}
        for fmt in self.SUPPORTED_FORMATS:
            fmt_hits = self.stats["hits_by_format"].get(fmt, 0)
            fmt_misses = self.stats["misses_by_format"].get(fmt, 0)
            fmt_total = fmt_hits + fmt_misses
            fmt_rate = (fmt_hits / fmt_total * 100) if fmt_total > 0 else 0
            if fmt_total > 0:  # Only include formats that were accessed
                hits_by_format[fmt] = {
                    "hits": fmt_hits,
                    "misses": fmt_misses,
                    "total": fmt_total,
                    "hit_rate": f"{fmt_rate:.1f}%"
                }

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "writes": self.stats["writes"],
            "expired": self.stats["expired"],
            "errors": self.stats["errors"],
            "cache_dir": str(self.cache_dir),
            "entries": len(list(self.cache_dir.glob("*.dat"))),
            "by_format": hits_by_format,  # Detailed breakdown by metadata format
            "supporting_docs_misses": self.stats["supporting_docs_misses"],  # Supporting doc misses
        }

    def _get_cache_path(self, identifier: str, format: str) -> Path:
        """Generate cache file path."""
        filename = f"{self._hash_key(identifier, format)}.dat"
        return self.cache_dir / filename

    def _get_meta_path(self, identifier: str, format: str) -> Path:
        """Generate metadata file path."""
        filename = f"{self._hash_key(identifier, format)}.meta"
        return self.cache_dir / filename

    def _hash_key(self, identifier: str, format: str) -> str:
        """Generate hash-based key for cache files."""
        key = f"{identifier}_{format}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _is_expired(self, meta_file: Path) -> bool:
        """Check if cache entry is expired."""
        try:
            metadata = json.loads(meta_file.read_text())
            expires_at = datetime.fromisoformat(metadata.get("expires_at", ""))
            return datetime.now() > expires_at
        except Exception:
            return True

    def _cleanup_cache(self, identifier: str, format: str) -> None:
        """Remove cache entry for identifier/format."""
        try:
            cache_file = self._get_cache_path(identifier, format)
            meta_file = self._get_meta_path(identifier, format)
            cache_file.unlink(missing_ok=True)
            meta_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


class CachedMetadataFetcher:
    """
    Wrapper for metadata fetchers with caching support.
    
    Automatically caches fetched content and returns cached data when available.
    """

    def __init__(
        self,
        cache: MetadataCache,
        ceh_extractor,  # CEHExtractor instance
    ):
        """
        Initialize cached fetcher.

        Args:
            cache: MetadataCache instance
            ceh_extractor: CEHExtractor instance for actual fetching
        """
        self.cache = cache
        self.ceh_extractor = ceh_extractor
        self.logger = get_logger(__name__)

    async def fetch_xml(self, identifier: str) -> Optional[str]:
        """Fetch XML with caching."""
        return await self._fetch_with_cache(
            identifier,
            "xml",
            self.ceh_extractor.fetch_dataset_xml,
        )

    async def fetch_json(self, identifier: str) -> Optional[str]:
        """Fetch JSON with caching."""
        return await self._fetch_with_cache(
            identifier,
            "json",
            self.ceh_extractor.fetch_dataset_json,
        )

    async def fetch_rdf(self, identifier: str) -> Optional[str]:
        """Fetch RDF with caching."""
        return await self._fetch_with_cache(
            identifier,
            "rdf",
            self.ceh_extractor.fetch_dataset_rdf,
        )

    async def fetch_schema_org(self, identifier: str) -> Optional[str]:
        """Fetch Schema.org with caching."""
        return await self._fetch_with_cache(
            identifier,
            "schema_org",
            self.ceh_extractor.fetch_dataset_schema_org,
        )

    async def _fetch_with_cache(
        self,
        identifier: str,
        format: str,
        fetch_func,
    ) -> Optional[str]:
        """
        Fetch with cache fallback.

        Args:
            identifier: Dataset identifier
            format: Metadata format
            fetch_func: Async function to fetch actual data

        Returns:
            Fetched/cached content, or None if failed
        """
        try:
            # Try cache first
            cached_content = await self.cache.get(identifier, format)
            if cached_content is not None:
                cache_size = len(cached_content) if isinstance(cached_content, str) else 0
                self.logger.info(
                    f"[{identifier}] ⚡ CACHED {format.upper()} ({cache_size} bytes)"
                )
                return cached_content

            # Fetch fresh data
            content = await fetch_func(identifier)
            if content:
                # Cache the fetched content ONLY if successful
                await self.cache.set(identifier, format, content)
                content_size = len(content) if isinstance(content, str) else 0
                self.logger.debug(
                    f"[{identifier}] Fetched and cached {format.upper()} ({content_size} bytes)"
                )
                return content

            # Failed fetch
            return None

        except Exception as e:
            self.logger.error(
                f"Error fetching {format} for {identifier}: {e}"
            )
            # Return None - don't recount cache stats
            return None
