"""
Error handling and recovery strategies for ETL pipeline.

Implements:
1. Automatic retries with exponential backoff
2. Circuit breaker pattern
3. Fallback mechanisms
4. Error categorization
5. Error recovery tracking
"""

import asyncio
import logging
from typing import Optional, Callable, Any, TypeVar, Coroutine, List, Dict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import random

from src.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategy options"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry mechanism"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True  # Add randomness to prevent thundering herd


class RecoverableError(Exception):
    """Base class for errors that can be recovered from"""
    pass


class NetworkError(RecoverableError):
    """Network-related error"""
    pass


class ParsingError(RecoverableError):
    """Metadata parsing error"""
    pass


class DatabaseError(RecoverableError):
    """Database operation error"""
    pass


class NonRecoverableError(Exception):
    """Base class for errors that cannot be recovered from"""
    pass


class ValidationError(NonRecoverableError):
    """Data validation error"""
    pass


class ETLErrorHandler:
    """
    Handles errors in ETL pipeline with configurable retry strategies.
    
    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker pattern
    - Fallback mechanisms
    - Error categorization
    - Error recovery tracking
    """
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        Initialize error handler.
        
        Args:
            retry_config: Configuration for retry mechanism
        """
        self.retry_config = retry_config or RetryConfig()
        self.failed_identifiers: set = set()
        self.recovered_identifiers: set = set()
        self.circuit_breaker_threshold = 0.5  # Break if 50% failures
        self.failure_count = 0
        self.success_count = 0
        self.error_history: List[Dict[str, Any]] = []
    
    async def execute_with_retry(
        self,
        coro_func: Callable[..., Coroutine[Any, Any, T]],
        identifier: str,
        operation_name: str,
        *args,
        **kwargs
    ) -> Optional[T]:
        """
        Execute async function with automatic retry logic.
        
        Args:
            coro_func: Async function to execute
            identifier: Dataset identifier (for logging)
            operation_name: Name of operation (for logging)
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if all retries exhausted
        """
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                logger.debug(
                    f"[{identifier}] Attempt {attempt + 1} of "
                    f"{self.retry_config.max_retries + 1}: {operation_name}"
                )
                
                result = await coro_func(*args, **kwargs)
                
                if attempt > 0:
                    self.recovered_identifiers.add(identifier)
                    logger.info(
                        f"[{identifier}] Successfully recovered after {attempt} retry/retries"
                    )
                
                self.success_count += 1
                return result
            
            except RecoverableError as e:
                last_error = e
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{identifier}] {operation_name} failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[{identifier}] {operation_name} failed after "
                        f"{self.retry_config.max_retries + 1} attempts"
                    )
            
            except NonRecoverableError as e:
                logger.error(f"[{identifier}] Non-recoverable error in {operation_name}: {e}")
                self.failure_count += 1
                self.failed_identifiers.add(identifier)
                self._record_error(identifier, operation_name, str(e), "non_recoverable")
                return None
            
            except Exception as e:
                logger.error(f"[{identifier}] Unexpected error in {operation_name}: {e}")
                self.failure_count += 1
                self.failed_identifiers.add(identifier)
                self._record_error(identifier, operation_name, str(e), "unexpected")
                return None
        
        self.failure_count += 1
        self.failed_identifiers.add(identifier)
        self._record_error(identifier, operation_name, str(last_error), "retry_exhausted")
        logger.error(f"[{identifier}] All retries exhausted for {operation_name}")
        return None
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay between retries based on strategy.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.initial_delay * (
                self.retry_config.backoff_multiplier ** attempt
            )
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.initial_delay * (attempt + 1)
        elif self.retry_config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.retry_config.initial_delay
        else:
            delay = 0
        
        # Cap maximum delay
        delay = min(delay, self.retry_config.max_delay)
        
        # Add jitter if enabled
        if self.retry_config.jitter and delay > 0:
            jitter = random.uniform(0, delay * 0.1)  # ±10% jitter
            delay += jitter
        
        return delay
    
    def should_continue(self) -> bool:
        """
        Determine if pipeline should continue based on circuit breaker logic.
        
        Circuit breaker opens if failure rate exceeds threshold.
        
        Returns:
            True if pipeline should continue, False if circuit breaker is open
        """
        total = self.success_count + self.failure_count
        
        if total == 0:
            return True
        
        failure_rate = self.failure_count / total
        
        if failure_rate > self.circuit_breaker_threshold:
            logger.critical(
                f"Circuit breaker opened: failure rate {failure_rate:.1%} "
                f"exceeds threshold {self.circuit_breaker_threshold:.1%}"
            )
            return False
        
        return True
    
    def _record_error(
        self,
        identifier: str,
        operation: str,
        message: str,
        error_type: str
    ):
        """Record error in history."""
        self.error_history.append({
            'identifier': identifier,
            'operation': operation,
            'message': message,
            'error_type': error_type,
            'timestamp': datetime.now(timezone.utc).isoformat()  # Use timezone.utc
        })
    
    def get_error_report(self) -> dict:
        """
        Get comprehensive error report.
        
        Returns:
            Dictionary with error statistics
        """
        total = self.success_count + self.failure_count
        
        return {
            'total_operations': total,
            'successful': self.success_count,
            'failed': self.failure_count,
            'success_rate': f"{(self.success_count / total * 100):.1f}%" if total > 0 else "0%",
            'failed_identifiers': list(self.failed_identifiers),
            'recovered_identifiers': list(self.recovered_identifiers),
            'recovery_count': len(self.recovered_identifiers),
            'error_history': self.error_history[-50:]  # Last 50 errors
        }
