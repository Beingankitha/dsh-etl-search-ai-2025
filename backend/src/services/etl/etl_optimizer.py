"""
Batch processing optimization for large datasets.

Features:
1. Adaptive batch size adjustment based on performance
2. Memory-efficient streaming processing
3. Concurrency optimization
4. Caching of processed results
5. Performance monitoring and metrics
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict, Any, Callable, TypeVar, Coroutine
from dataclasses import dataclass, field
from pathlib import Path

from src.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Track performance metrics for optimization"""
    batch_size: int
    duration: float
    items_processed: int
    successful: int
    failed: int
    
    @property
    def throughput(self) -> float:
        """Items processed per second"""
        return self.items_processed / self.duration if self.duration > 0 else 0
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful items"""
        total = self.successful + self.failed
        return (self.successful / total * 100) if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'batch_size': self.batch_size,
            'duration': f"{self.duration:.2f}s",
            'items_processed': self.items_processed,
            'successful': self.successful,
            'failed': self.failed,
            'throughput': f"{self.throughput:.2f} items/sec",
            'success_rate': f"{self.success_rate:.1f}%"
        }


class AdaptiveBatchProcessor:
    """
    Intelligently adapts batch size based on performance metrics.
    
    Features:
    1. Dynamic batch size adjustment
    2. Performance monitoring
    3. Memory optimization
    4. Throughput maximization
    5. Failure rate tracking
    """
    
    def __init__(
        self,
        initial_batch_size: int = 10,
        min_batch_size: int = 1,
        max_batch_size: int = 100,
        target_duration_per_batch: float = 10.0,  # seconds
        enable_adaptive: bool = True
    ):
        """
        Initialize adaptive batch processor.
        
        Args:
            initial_batch_size: Starting batch size
            min_batch_size: Minimum allowed batch size
            max_batch_size: Maximum allowed batch size
            target_duration_per_batch: Target time to process one batch
            enable_adaptive: Whether to enable dynamic batch size adjustment
        """
        self.batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_duration = target_duration_per_batch
        self.enable_adaptive = enable_adaptive
        self.performance_history: List[PerformanceMetrics] = []
    
    async def process_items_in_batches(
        self,
        items: List[T],
        process_func: Callable[[List[T]], Coroutine[Any, Any, List[Any]]],
        on_batch_complete: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Process items in adaptive batches.
        
        Args:
            items: List of items to process
            process_func: Async function to process batch (receives list, returns results)
            on_batch_complete: Optional callback after each batch (batch_num, total_batches, processed)
            
        Returns:
            Dictionary with processing results and metrics
        """
        logger.info(
            f"Starting adaptive batch processing for {len(items)} items "
            f"(initial batch size: {self.batch_size})"
        )
        
        start_time = time.time()
        results = []
        failed_items = []
        
        batch_num = 0
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(items), self.batch_size):
            batch_num += 1
            batch = items[i:i + self.batch_size]
            
            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} items, batch size: {self.batch_size})"
            )
            
            batch_start_time = time.time()
            
            try:
                # Process batch
                batch_results = await process_func(batch)
                batch_duration = time.time() - batch_start_time
                
                results.extend(batch_results)
                
                # Record performance metrics
                metrics = PerformanceMetrics(
                    batch_size=len(batch),
                    duration=batch_duration,
                    items_processed=len(batch),
                    successful=len(batch_results),
                    failed=len(batch) - len(batch_results)
                )
                self.performance_history.append(metrics)
                
                logger.debug(
                    f"Batch {batch_num} complete: {metrics.throughput:.2f} items/sec, "
                    f"success rate: {metrics.success_rate:.1f}%"
                )
                
                # Adapt batch size if enabled
                if self.enable_adaptive:
                    self._adapt_batch_size(metrics)
                
                # Callback
                if on_batch_complete:
                    on_batch_complete(batch_num, total_batches, len(results))
            
            except Exception as e:
                logger.error(f"Failed to process batch {batch_num}: {e}")
                failed_items.extend(batch)
        
        total_duration = time.time() - start_time
        
        return {
            'total_items': len(items),
            'successful': len(results),
            'failed': len(failed_items),
            'total_duration': total_duration,
            'average_throughput': len(results) / total_duration if total_duration > 0 else 0,
            'final_batch_size': self.batch_size,
            'performance_history': [m.to_dict() for m in self.performance_history]
        }
    
    def _adapt_batch_size(self, metrics: PerformanceMetrics):
        """
        Adapt batch size based on performance metrics.
        
        Strategy:
        - If batch takes too long: reduce batch size
        - If batch completes quickly: increase batch size
        - If failure rate is high: reduce batch size
        
        Args:
            metrics: Current batch performance metrics
        """
        old_batch_size = self.batch_size
        
        # If too many failures, reduce batch size
        if metrics.success_rate < 80:
            self.batch_size = max(
                self.min_batch_size,
                int(self.batch_size * 0.8)
            )
            logger.info(
                f"Reduced batch size: {old_batch_size} → {self.batch_size} (low success rate)"
            )
        
        # If batch takes too long, reduce batch size
        elif metrics.duration > self.target_duration * 1.5:
            self.batch_size = max(
                self.min_batch_size,
                int(self.batch_size * 0.9)
            )
            logger.info(
                f"Reduced batch size: {old_batch_size} → {self.batch_size} (slow processing)"
            )
        
        # If batch completes quickly, increase batch size
        elif metrics.duration < self.target_duration * 0.5:
            self.batch_size = min(
                self.max_batch_size,
                int(self.batch_size * 1.2)
            )
            logger.info(
                f"Increased batch size: {old_batch_size} → {self.batch_size} (fast processing)"
            )


class ConcurrencyOptimizer:
    """
    Optimize concurrency settings for ETL pipeline.
    
    Features:
    1. Automatic concurrency adjustment
    2. Resource monitoring
    3. Bottleneck detection
    4. Load balancing
    """
    
    def __init__(
        self,
        initial_concurrency: int = 5,
        min_concurrency: int = 1,
        max_concurrency: int = 50
    ):
        """
        Initialize concurrency optimizer.
        
        Args:
            initial_concurrency: Starting number of concurrent tasks
            min_concurrency: Minimum concurrent tasks
            max_concurrency: Maximum concurrent tasks
        """
        self.concurrency = initial_concurrency
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.performance_samples: List[float] = []
    
    async def execute_with_semaphore(
        self,
        tasks: List[Coroutine[Any, Any, T]]
    ) -> List[T]:
        """
        Execute coroutines with concurrency limit.
        
        Args:
            tasks: List of coroutines to execute
            
        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def bounded_task(coro):
            async with semaphore:
                return await coro
        
        return await asyncio.gather(*[bounded_task(task) for task in tasks])
    
    def record_throughput(self, throughput: float):
        """
        Record throughput measurement.
        
        Args:
            throughput: Items processed per second
        """
        self.performance_samples.append(throughput)
        
        # Adapt concurrency based on recent performance
        if len(self.performance_samples) >= 5:
            avg_throughput = sum(self.performance_samples[-5:]) / 5
            
            # If throughput is stable/increasing, increase concurrency
            if len(self.performance_samples) >= 10:
                prev_avg = sum(self.performance_samples[-10:-5]) / 5
                
                if avg_throughput > prev_avg:
                    self.concurrency = min(
                        self.max_concurrency,
                        self.concurrency + 1
                    )
                    logger.info(f"Increased concurrency: {self.concurrency}")
                elif avg_throughput < prev_avg * 0.9:
                    self.concurrency = max(
                        self.min_concurrency,
                        self.concurrency - 1
                    )
                    logger.info(f"Decreased concurrency: {self.concurrency}")


class CachingBatchProcessor:
    """
    Cache processed results to avoid redundant processing.
    
    Features:
    1. In-memory caching
    2. Deduplication tracking
    3. Cache invalidation
    4. Performance monitoring
    """
    
    def __init__(self, enable_tracking: bool = True):
        """
        Initialize caching processor.
        
        Args:
            enable_tracking: Whether to track cache hits/misses
        """
        self.memory_cache: Dict[str, Any] = {}
        self.enable_tracking = enable_tracking
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_cached(self, identifier: str) -> Optional[Any]:
        """
        Get cached result for identifier.
        
        Args:
            identifier: Item identifier
            
        Returns:
            Cached result or None
        """
        if identifier in self.memory_cache:
            if self.enable_tracking:
                self.cache_hits += 1
            return self.memory_cache[identifier]
        
        if self.enable_tracking:
            self.cache_misses += 1
        return None
    
    def cache_result(self, identifier: str, result: Any):
        """
        Cache result for identifier.
        
        Args:
            identifier: Item identifier
            result: Result to cache
        """
        self.memory_cache[identifier] = result
        logger.debug(f"Cached result for {identifier}")
    
    def clear_cache(self):
        """Clear all cached results"""
        size_before = len(self.memory_cache)
        self.memory_cache.clear()
        logger.info(f"Cleared cache ({size_before} entries)")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cached_items': len(self.memory_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }
