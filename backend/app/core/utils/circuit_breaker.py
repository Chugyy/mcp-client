# app/core/utils/circuit_breaker.py
"""Circuit breaker pattern implementation for external service calls."""

from enum import Enum
from datetime import datetime, timedelta, timezone
import asyncio
from typing import Callable, Any, Optional
from config.logger import logger
from app.core.exceptions import CircuitBreakerOpenError


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failures detected, blocking calls
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for protecting external service calls.

    States:
    - CLOSED: Normal operation, all requests proceed
    - OPEN: Failure threshold reached, requests fail fast
    - HALF_OPEN: Testing recovery with limited requests

    Example:
        circuit = CircuitBreaker(name="anthropic", failure_threshold=5)
        result = await circuit.call(adapter.chat, model, messages, **kwargs)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 1
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit identifier (e.g., "anthropic", "openai")
            failure_threshold: Consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Successful calls in HALF_OPEN to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func execution

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN and recovery timeout not reached
        """
        async with self._lock:
            # Check if circuit should transition to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name}: OPEN → HALF_OPEN")
                else:
                    seconds_until_retry = self._seconds_until_retry()
                    raise CircuitBreakerOpenError(
                        f"Provider {self.name} is temporarily unavailable. Retry in {seconds_until_retry}s."
                    )

        # Execute function
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise

    async def record_success(self):
        """Record successful call and update circuit state."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker {self.name}: HALF_OPEN → CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # Reset failure count on success

    async def record_failure(self):
        """Record failed call and update circuit state."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name}: HALF_OPEN → OPEN (recovery failed)")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.error(f"Circuit breaker {self.name}: CLOSED → OPEN ({self.failure_count} failures)")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _seconds_until_retry(self) -> int:
        """Calculate seconds until next retry attempt."""
        if not self.last_failure_time:
            return 0

        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return max(0, int(self.recovery_timeout - elapsed))

    def get_state(self) -> dict:
        """
        Return current circuit state.

        Returns:
            Dict with circuit name, state, failure count, and retry information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "seconds_until_retry": self._seconds_until_retry() if self.state == CircuitState.OPEN else None
        }
