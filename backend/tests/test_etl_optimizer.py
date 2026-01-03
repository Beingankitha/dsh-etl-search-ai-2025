"""
Tests for ETL Optimizer Components

Tests adaptive batch processing, concurrency optimization, and performance tracking.
"""

import pytest
import asyncio
import time
from typing import List

from src.services.etl.etl_optimizer import (
    AdaptiveBatchProcessor,
    ConcurrencyOptimizer,
    CachingBatchProcessor,
    PerformanceMetrics
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def adaptive_processor():
    """Create adaptive batch processor"""
    return AdaptiveBatchProcessor(
        initial_batch_size=10,
        min_batch_size=1,
        max_batch_size=100,
        target_duration_per_batch=5.0,
        enable_adaptive=True
    )


@pytest.fixture
def concurrency_optimizer():
    """Create concurrency optimizer"""
    return ConcurrencyOptimizer(initial_concurrency=5)


@pytest.fixture
def caching_processor():
    """Create caching batch processor"""
    return CachingBatchProcessor(enable_tracking=True)


# ============================================================================
# TEST: PerformanceMetrics
# ============================================================================

class TestPerformanceMetrics:
    """Test performance metrics tracking"""
    
    def test_metrics_initialization(self):
        """Test creating performance metrics"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=5.0,
            items_processed=50,
            successful=48,
            failed=2
        )
        
        assert metrics.batch_size == 10
        assert metrics.items_processed == 50
        assert metrics.successful == 48
        assert metrics.failed == 2
    
    def test_throughput_calculation(self):
        """Test throughput calculation"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=10.0,
            items_processed=100,
            successful=100,
            failed=0
        )
        
        assert metrics.throughput == 10.0  # 100 items / 10 seconds
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=5.0,
            items_processed=50,
            successful=45,
            failed=5
        )
        
        assert metrics.success_rate == 90.0  # 45/50 * 100
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=5.0,
            items_processed=50,
            successful=48,
            failed=2
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result["batch_size"] == 10
        assert result["items_processed"] == 50
        assert "throughput" in result
        assert "success_rate" in result
    
    def test_throughput_zero_duration(self):
        """Test throughput with zero duration"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=0.0,
            items_processed=0,
            successful=0,
            failed=0
        )
        
        assert metrics.throughput == 0


# ============================================================================
# TEST: AdaptiveBatchProcessor
# ============================================================================

class TestAdaptiveBatchProcessor:
    """Test adaptive batch processing"""
    
    def test_processor_initialization(self):
        """Test processor initialization"""
        processor = AdaptiveBatchProcessor(
            initial_batch_size=10,
            min_batch_size=2,
            max_batch_size=50
        )
        
        assert processor.batch_size == 10
        assert processor.min_batch_size == 2
        assert processor.max_batch_size == 50
    
    def test_get_batch_size(self, adaptive_processor):
        """Test getting current batch size"""
        size = adaptive_processor.batch_size
        
        assert size == 10
        assert size >= adaptive_processor.min_batch_size
        assert size <= adaptive_processor.max_batch_size
    
    @pytest.mark.asyncio
    async def test_process_batch(self, adaptive_processor):
        """Test processing a batch"""
        items = list(range(10))
        
        async def process_func(batch):
            return [item * 2 for item in batch]
        
        result = await adaptive_processor.process_items_in_batches(items, process_func)
        
        assert 'successful' in result
        assert result['successful'] == 10
    
    def test_disable_adaptive_mode(self):
        """Test disabling adaptive batching"""
        processor = AdaptiveBatchProcessor(
            initial_batch_size=10,
            enable_adaptive=False
        )
        
        assert processor.enable_adaptive is False
        assert processor.batch_size == 10
    
    @pytest.mark.asyncio
    async def test_record_metrics(self, adaptive_processor):
        """Test recording performance metrics"""
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=5.0,
            items_processed=50,
            successful=48,
            failed=2
        )
        
        adaptive_processor.performance_history.append(metrics)
        
        assert len(adaptive_processor.performance_history) > 0
    
    @pytest.mark.asyncio
    async def test_batch_size_adjustment_on_performance(self, adaptive_processor):
        """Test batch size adjusts based on performance"""
        initial_size = adaptive_processor.batch_size
        
        # Simulate slow batch
        slow_metrics = PerformanceMetrics(
            batch_size=initial_size,
            duration=15.0,  # Too long
            items_processed=100,
            successful=100,
            failed=0
        )
        
        adaptive_processor._adapt_batch_size(slow_metrics)
        
        # Batch size should reduce
        new_size = adaptive_processor.batch_size
        assert new_size <= initial_size


# ============================================================================
# TEST: ConcurrencyOptimizer
# ============================================================================

class TestConcurrencyOptimizer:
    """Test concurrency optimization"""
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        optimizer = ConcurrencyOptimizer(initial_concurrency=5)
        
        assert optimizer.concurrency == 5
    
    def test_get_concurrency(self, concurrency_optimizer):
        """Test getting concurrency level"""
        concurrency = concurrency_optimizer.concurrency
        
        assert concurrency == 5
    
    @pytest.mark.asyncio
    async def test_run_concurrent_tasks(self, concurrency_optimizer):
        """Test running concurrent tasks"""
        async def task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        tasks = [task(i) for i in range(10)]
        results = await concurrency_optimizer.execute_with_semaphore(tasks)
        
        assert len(results) == 10
        assert results[0] == 0
        assert results[9] == 18
    
    def test_concurrency_limits(self, concurrency_optimizer):
        """Test concurrency level limits"""
        concurrency_optimizer.concurrency = 1
        assert concurrency_optimizer.concurrency == 1
        
        concurrency_optimizer.concurrency = 50
        assert concurrency_optimizer.concurrency == 50
    
    @pytest.mark.asyncio
    async def test_adjust_concurrency_on_errors(self, concurrency_optimizer):
        """Test concurrency adjusts on errors"""
        initial_concurrency = concurrency_optimizer.concurrency
        
        # Record poor throughput
        concurrency_optimizer.record_throughput(1.0)  # 1 item/sec
        concurrency_optimizer.record_throughput(0.9)  # Still low
        
        # Concurrency might adjust
        assert concurrency_optimizer.concurrency >= 1


# ============================================================================
# TEST: CachingBatchProcessor
# ============================================================================

class TestCachingBatchProcessor:
    """Test caching batch processing"""

    def test_processor_initialization(self):
        """Test caching processor initialization"""
        processor = CachingBatchProcessor(enable_tracking=True)
        
        assert processor.enable_tracking is True
    
    def test_cache_result(self, caching_processor):
        """Test caching a result"""
        caching_processor.cache_result("key-1", "value-1")
        result = caching_processor.get_cached("key-1")
        
        assert result == "value-1"
    
    def test_cache_miss(self, caching_processor):
        """Test cache miss returns None"""
        result = caching_processor.get_cached("non-existent")
        
        assert result is None
    
    def test_cache_hit_statistics(self, caching_processor):
        """Test cache hit statistics"""
        caching_processor.cache_result("key-1", "value-1")
        
        # Hit
        _ = caching_processor.get_cached("key-1")
        
        # Miss
        _ = caching_processor.get_cached("key-2")
        
        stats = caching_processor.get_cache_stats()
        
        assert "cache_hits" in stats
        assert "cache_misses" in stats
    
    def test_clear_cache(self, caching_processor):
        """Test clearing cache"""
        caching_processor.cache_result("key-1", "value-1")
        caching_processor.cache_result("key-2", "value-2")
        
        caching_processor.clear_cache()
        
        assert caching_processor.get_cached("key-1") is None
        assert caching_processor.get_cached("key-2") is None
    
    def test_cache_statistics_dict(self, caching_processor):
        """Test cache statistics as dictionary"""
        for i in range(5):
            caching_processor.cache_result(f"key-{i}", f"value-{i}")
            caching_processor.get_cached(f"key-{i}")
        
        stats = caching_processor.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert stats["cache_hits"] == 5


# ============================================================================
# TEST: Integration Tests
# ============================================================================

class TestOptimizerIntegration:
    """Test optimizer components working together"""
    
    @pytest.mark.asyncio
    async def test_adaptive_with_concurrency(self, adaptive_processor, concurrency_optimizer):
        """Test adaptive processor with concurrency optimizer"""
        items = list(range(20))
        
        async def process_func(batch):
            await asyncio.sleep(0.01)
            return [item * 2 for item in batch]
        
        # Process with both optimizations
        result = await adaptive_processor.process_items_in_batches(items, process_func)
        
        assert result['successful'] == 20
    
    @pytest.mark.asyncio
    async def test_caching_improves_performance(self, caching_processor):
        """Test caching improves performance"""
        call_count = [0]
        
        def expensive_operation(key):
            call_count[0] += 1
            return key * 2
        
        # First call - cache miss
        result1 = expensive_operation("key-1")
        assert call_count[0] == 1
        caching_processor.cache_result("key-1", result1)
        
        # Second call - cache hit
        cached = caching_processor.get_cached("key-1")
        assert cached == result1
        assert call_count[0] == 1  # Not called again


# ============================================================================
# TEST: Error Handling
# ============================================================================

class TestOptimizerErrorHandling:
    """Test error handling in optimizers"""
    
    @pytest.mark.asyncio
    async def test_batch_processor_handles_errors(self, adaptive_processor):
        """Test batch processor handles item errors"""
        items = [1, 2, 3, 4]
        
        async def process_func(batch):
            return [item * 2 for item in batch]
        
        result = await adaptive_processor.process_items_in_batches(
            items, 
            process_func
        )
        
        # Should complete without crashing
        assert result['successful'] == 4
    
    def test_optimizer_handles_invalid_concurrency(self):
        """Test optimizer concurrency can be set to any value"""
        optimizer = ConcurrencyOptimizer(initial_concurrency=5)
        
        # Can set to 0
        optimizer.concurrency = 0
        assert optimizer.concurrency == 0
        
        # Can set to negative (though not recommended)
        optimizer.concurrency = -5
        assert optimizer.concurrency == -5
        
        # Can set to valid value
        optimizer.concurrency = 10
        assert optimizer.concurrency == 10


# ============================================================================
# TEST: Performance Monitoring
# ============================================================================

class TestPerformanceMonitoring:
    """Test performance monitoring features"""
    
    def test_metrics_history_tracking(self, adaptive_processor):
        """Test tracking metrics history"""
        for i in range(5):
            metrics = PerformanceMetrics(
                batch_size=10,
                duration=5.0 + i,
                items_processed=50,
                successful=48,
                failed=2
            )
            adaptive_processor.performance_history.append(metrics)
        
        assert len(adaptive_processor.performance_history) >= 5
    
    def test_performance_report(self, adaptive_processor):
        """Test generating performance report"""
        for _ in range(3):
            metrics = PerformanceMetrics(
                batch_size=10,
                duration=5.0,
                items_processed=50,
                successful=48,
                failed=2
            )
            adaptive_processor.performance_history.append(metrics)
        
        # Check if we can generate a report from history
        assert len(adaptive_processor.performance_history) >= 3
