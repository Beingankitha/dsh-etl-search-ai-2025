"""
ETL Service Module - Pipeline Orchestration and Error Handling

This module contains the core ETL pipeline orchestrator and supporting error handling/optimization utilities.

Classes:
    - ETLService: Main orchestrator for the 3-phase pipeline (EXTRACT → TRANSFORM → LOAD)
    - ETLErrorHandler: Handles errors with retry logic and recovery strategies
    - RetryConfig: Configuration for retry behavior
    - RetryStrategy: Enum for retry strategies
    - AdaptiveBatchProcessor: Dynamically adjusts batch sizes based on performance
    - ConcurrencyOptimizer: Optimizes concurrent operations
    - CachingBatchProcessor: Caches batch processing results

Usage:
    from src.services.etl import ETLService, RetryConfig, AdaptiveBatchProcessor
    
    # Initialize services
    service = ETLService(
        identifiers_file=Path("identifiers.txt"),
        unit_of_work=unit_of_work,
        batch_size=10
    )
    
    # Run pipeline
    await service.run_pipeline(verbose=True)
    
    # Use adaptive batch processing
    processor = AdaptiveBatchProcessor(initial_size=10)
    await processor.process_batch(items, process_func)
"""

from .etl_service import ETLService
from .etl_error_handler import (
    ETLErrorHandler,
    RetryConfig,
    RetryStrategy,
    RecoverableError,
    NonRecoverableError,
    NetworkError,
    ParsingError,
    DatabaseError,
    ValidationError,
)
from .etl_optimizer import (
    AdaptiveBatchProcessor,
    ConcurrencyOptimizer,
    CachingBatchProcessor,
    PerformanceMetrics,
)

__all__ = [
    # Main orchestrator
    "ETLService",
    # Error handling
    "ETLErrorHandler",
    "RetryConfig",
    "RetryStrategy",
    "RecoverableError",
    "NonRecoverableError",
    "NetworkError",
    "ParsingError",
    "DatabaseError",
    "ValidationError",
    # Optimization
    "AdaptiveBatchProcessor",
    "ConcurrencyOptimizer",
    "CachingBatchProcessor",
    "PerformanceMetrics",
]
