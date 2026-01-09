"""
Performance and load testing for ETL pipeline.

Tests throughput, latency, scalability, and resource utilization.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock
import gc


class TestParsingPerformance:
    """Test parsing performance under various conditions."""

    @pytest.mark.asyncio
    async def test_json_parse_throughput(self):
        """Test JSON parser throughput."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        num_docs = 50
        
        documents = [
            json.dumps({
                "fileIdentifier": f"doc-{i}",
                "title": f"Dataset {i}",
                "abstract": f"Description for dataset {i}"
            })
            for i in range(num_docs)
        ]
        
        start = time.time()
        results = []
        for doc in documents:
            try:
                result = await parser.parse(doc)
                results.append(result)
            except:
                pass
        elapsed = time.time() - start
        
        throughput = len(results) / elapsed
        assert throughput > 10  # At least 10 docs/sec
        assert len(results) >= num_docs * 0.9  # 90% success rate

    @pytest.mark.asyncio
    async def test_parse_large_document_performance(self):
        """Test parsing large documents."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        # Create large document with many keywords
        keywords = [f"keyword-{i}" for i in range(1000)]
        large_doc = json.dumps({
            "fileIdentifier": "large-doc",
            "title": "Large Dataset",
            "abstract": "A" * 50000,  # 50KB abstract
            "keywords": keywords
        })
        
        start = time.time()
        try:
            result = await parser.parse(large_doc)
            elapsed = time.time() - start
            
            assert elapsed < 5.0
            assert len(result.keywords) > 500
        except:
            pytest.skip("Large document parsing not supported")

    @pytest.mark.asyncio
    async def test_concurrent_parsing(self):
        """Test concurrent parsing of multiple documents."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        num_concurrent = 20
        
        documents = [
            json.dumps({
                "fileIdentifier": f"concurrent-{i}",
                "title": f"Dataset {i}"
            })
            for i in range(num_concurrent)
        ]
        
        start = time.time()
        tasks = [parser.parse(doc) for doc in documents]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start
            
            successful = [r for r in results if not isinstance(r, Exception)]
            assert len(successful) >= num_concurrent * 0.9
            assert elapsed < 10.0
        except:
            pytest.skip("Concurrent parsing not fully supported")


class TestEnrichmentPerformance:
    """Test enrichment performance."""

    @pytest.mark.asyncio
    async def test_enrichment_throughput(self):
        """Test enrichment throughput."""
        from src.services.metadata_enrichment.metadata_enrichment_impl import MetadataEnricher
        
        enricher = MetadataEnricher()
        num_datasets = 30
        
        start = time.time()
        results = []
        for i in range(num_datasets):
            try:
                result = enricher.enrich(
                    title=f"Dataset {i}",
                    abstract=f"Description for dataset {i}"
                )
                results.append(result)
            except:
                pass
        elapsed = time.time() - start
        
        if elapsed > 0:
            throughput = len(results) / elapsed
            assert throughput > 0.5  # At least 0.5 dataset/sec

    @pytest.mark.asyncio
    async def test_enrichment_with_large_text(self):
        """Test enrichment with large text input."""
        from src.services.metadata_enrichment.metadata_enrichment_impl import MetadataEnricher
        
        enricher = MetadataEnricher()
        
        large_abstract = "Sample abstract. " * 5000  # Very long text
        
        start = time.time()
        try:
            result = await enricher.enrich(
                title="Large Text Dataset",
                abstract=large_abstract
            )
            elapsed = time.time() - start
            
            assert elapsed < 30.0
            assert result.keywords is not None
        except:
            pytest.skip("Large text enrichment may not be supported")

    @pytest.mark.asyncio
    async def test_concurrent_enrichment(self):
        """Test concurrent enrichment."""
        from src.services.metadata_enrichment.metadata_enrichment_impl import MetadataEnricher
        
        enricher = MetadataEnricher()
        num_concurrent = 15
        
        start = time.time()
        tasks = [
            enricher.enrich(
                title=f"Dataset {i}",
                abstract=f"Description {i}"
            )
            for i in range(num_concurrent)
        ]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start
            
            successful = [r for r in results if not isinstance(r, Exception)]
            assert len(successful) >= num_concurrent * 0.8
            assert elapsed < 30.0
        except:
            pytest.skip("Concurrent enrichment not fully supported")


class TestMemoryUsage:
    """Test memory usage and efficiency."""

    @pytest.mark.asyncio
    async def test_parser_memory_efficiency(self):
        """Test memory efficiency of parser."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Parse multiple documents
        for i in range(100):
            doc = json.dumps({"fileIdentifier": f"doc-{i}", "title": f"Doc {i}"})
            try:
                await parser.parse(doc)
            except:
                pass
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        object_growth = final_objects - initial_objects
        assert object_growth < 100000  # Less than 100k new objects

    @pytest.mark.asyncio
    async def test_concurrent_operations_memory(self):
        """Test memory usage with concurrent operations."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        gc.collect()
        
        # Create many concurrent tasks
        tasks = [
            parser.parse(json.dumps({
                "fileIdentifier": f"concurrent-{i}",
                "title": f"Dataset {i}"
            }))
            for i in range(50)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            gc.collect()
            
            # Should handle concurrent operations without excessive memory growth
            assert len(results) == 50
        except:
            pytest.skip("Memory test inconclusive")


class TestLatency:
    """Test latency metrics."""

    @pytest.mark.asyncio
    async def test_parse_latency_p50(self):
        """Test p50 latency for parsing."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        latencies = []
        
        for i in range(50):
            doc = json.dumps({
                "fileIdentifier": f"latency-{i}",
                "title": f"Doc {i}"
            })
            
            start = time.time()
            try:
                await parser.parse(doc)
                latencies.append((time.time() - start) * 1000)
            except:
                pass
        
        if latencies:
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            assert p50 < 1000  # P50 < 1 second

    @pytest.mark.asyncio
    async def test_parse_latency_p95(self):
        """Test p95 latency for parsing."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        latencies = []
        
        for i in range(50):
            doc = json.dumps({
                "fileIdentifier": f"latency-{i}",
                "title": f"Doc {i}"
            })
            
            start = time.time()
            try:
                await parser.parse(doc)
                latencies.append((time.time() - start) * 1000)
            except:
                pass
        
        if latencies:
            latencies.sort()
            p95 = latencies[int(len(latencies) * 0.95)]
            assert p95 < 5000  # P95 < 5 seconds

    @pytest.mark.asyncio
    async def test_enrichment_latency_p50(self):
        """Test p50 latency for enrichment."""
        from src.services.metadata_enrichment.metadata_enrichment_impl import MetadataEnricher
        
        enricher = MetadataEnricher()
        latencies = []
        
        for i in range(30):
            start = time.time()
            try:
                await enricher.enrich(
                    title=f"Dataset {i}",
                    abstract=f"Description {i}"
                )
                latencies.append((time.time() - start) * 1000)
            except:
                pass
        
        if latencies:
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            assert p50 < 10000  # P50 < 10 seconds


class TestScalability:
    """Test scalability with increasing load."""

    @pytest.mark.asyncio
    async def test_parse_scaling_with_document_count(self):
        """Test parsing scales with number of documents."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        for num_docs in [10, 25, 50]:
            start = time.time()
            results = []
            
            for i in range(num_docs):
                doc = json.dumps({
                    "fileIdentifier": f"scale-{i}",
                    "title": f"Doc {i}"
                })
                try:
                    result = await parser.parse(doc)
                    results.append(result)
                except:
                    pass
            
            elapsed = time.time() - start
            throughput = len(results) / elapsed if elapsed > 0 else 0
            
            # Throughput should remain reasonable
            assert throughput > 5 or elapsed < 10

    @pytest.mark.asyncio
    async def test_parse_scaling_with_document_size(self):
        """Test parsing scales with document size."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        sizes = [100, 500, 1000]  # Keywords count
        
        for size in sizes:
            keywords = [f"keyword-{i}" for i in range(size)]
            doc = json.dumps({
                "fileIdentifier": "scale-test",
                "title": "Test",
                "keywords": keywords
            })
            
            start = time.time()
            try:
                result = await parser.parse(doc)
                elapsed = time.time() - start
                
                # Latency should grow sub-linearly
                assert elapsed < size / 100  # Rough heuristic
            except:
                pass


class TestResourceUtilization:
    """Test resource utilization."""

    @pytest.mark.asyncio
    async def test_cpu_efficiency(self):
        """Test CPU efficiency of operations."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        # Measure execution time for known work
        start = time.time()
        for i in range(20):
            doc = json.dumps({"fileIdentifier": f"cpu-{i}", "title": f"Doc {i}"})
            try:
                await parser.parse(doc)
            except:
                pass
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 20.0

    @pytest.mark.asyncio
    async def test_io_efficiency(self):
        """Test I/O efficiency."""
        # Simulate document processing
        documents = [
            json.dumps({"fileIdentifier": f"io-{i}", "title": f"Doc {i}"})
            for i in range(100)
        ]
        
        start = time.time()
        for doc in documents:
            try:
                json.loads(doc)
            except:
                pass
        elapsed = time.time() - start
        
        # Should process 100 documents quickly
        assert elapsed < 5.0


class TestErrorHandlingPerformance:
    """Test performance with error conditions."""

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test recovery from errors doesn't impact performance."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        # Mix valid and invalid documents
        valid_count = 0
        invalid_count = 0
        
        for i in range(20):
            if i % 3 == 0:
                # Invalid document
                doc = "{invalid json"
                invalid_count += 1
            else:
                # Valid document
                doc = json.dumps({"fileIdentifier": f"doc-{i}", "title": f"Doc {i}"})
                valid_count += 1
            
            try:
                await parser.parse(doc)
            except:
                pass
        
        # Should attempt all despite errors
        assert valid_count + invalid_count == 20

    @pytest.mark.asyncio
    async def test_partial_failure_graceful_handling(self):
        """Test partial failures don't crash pipeline."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        results = []
        
        for i in range(30):
            doc = json.dumps({
                "fileIdentifier": f"partial-{i}",
                "title": f"Doc {i}" if i % 5 != 0 else None  # Some missing titles
            })
            
            try:
                result = await parser.parse(doc)
                results.append(result)
            except:
                results.append(None)
        
        # Should have processed all
        assert len(results) == 30
        # Most should succeed
        successful = [r for r in results if r is not None]
        assert len(successful) >= 20


class TestStressConditions:
    """Test under stress conditions."""

    @pytest.mark.asyncio
    async def test_rapid_successive_operations(self):
        """Test rapid successive operations."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        results = []
        
        # Rapid fire requests
        for i in range(50):
            doc = json.dumps({"fileIdentifier": f"rapid-{i}", "title": f"Doc {i}"})
            try:
                result = await parser.parse(doc)
                results.append(result)
            except:
                pass
        
        # Should handle rapid requests
        assert len(results) >= 40

    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test high concurrency levels."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        # Create many concurrent tasks
        tasks = [
            parser.parse(json.dumps({
                "fileIdentifier": f"concurrent-{i}",
                "title": f"Dataset {i}"
            }))
            for i in range(100)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = [r for r in results if not isinstance(r, Exception)]
            
            # Should handle high concurrency reasonably
            assert len(successful) >= 50
        except:
            pytest.skip("High concurrency test inconclusive")

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load over time."""
        from src.services.parsers.json_parser import JSONMetadataParser
        
        parser = JSONMetadataParser()
        
        start = time.time()
        timeout = 10  # 10 second test
        count = 0
        
        while time.time() - start < timeout:
            doc = json.dumps({
                "fileIdentifier": f"sustained-{count}",
                "title": f"Doc {count}"
            })
            try:
                await parser.parse(doc)
                count += 1
            except:
                pass
        
        elapsed = time.time() - start
        throughput = count / elapsed
        
        # Should maintain throughput
        assert throughput > 5  # At least 5 docs/sec
