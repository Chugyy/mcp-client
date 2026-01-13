#!/usr/bin/env python3
# tests/unit/llm/test_circuit_breaker.py
"""Unit tests for circuit breaker implementation."""

import pytest
import asyncio
from datetime import datetime, timedelta
from app.core.utils.circuit_breaker import CircuitBreaker, CircuitState
from app.core.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_closed_to_open_after_threshold(self):
        """Circuit should open after reaching failure threshold."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        # Record 5 failures
        for _ in range(5):
            await circuit.record_failure()

        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count == 5

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=1)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Attempt to call should transition to HALF_OPEN
        async def dummy_func():
            return "success"

        result = await circuit.call(dummy_func)
        assert result == "success"
        assert circuit.state == CircuitState.CLOSED  # Success in HALF_OPEN closes circuit

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """Circuit should close after successful call in HALF_OPEN state."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=1)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        # Manually set to HALF_OPEN and test success
        circuit.state = CircuitState.HALF_OPEN
        await circuit.record_success()

        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Circuit should reopen on failure in HALF_OPEN state."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=1)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        # Manually set to HALF_OPEN and test failure
        circuit.state = CircuitState.HALF_OPEN
        await circuit.record_failure()

        assert circuit.state == CircuitState.OPEN


class TestCircuitBreakerFailureThreshold:
    """Test failure counting and threshold behavior."""

    @pytest.mark.asyncio
    async def test_failure_count_increments(self):
        """Failure count should increment on each failure."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        await circuit.record_failure()
        assert circuit.failure_count == 1

        await circuit.record_failure()
        assert circuit.failure_count == 2

        await circuit.record_failure()
        assert circuit.failure_count == 3

    @pytest.mark.asyncio
    async def test_success_resets_failure_count_in_closed(self):
        """Success should reset failure count in CLOSED state."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        # Record some failures
        await circuit.record_failure()
        await circuit.record_failure()
        assert circuit.failure_count == 2

        # Success resets count
        await circuit.record_success()
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_consecutive_failures_required(self):
        """Only consecutive failures should trigger circuit opening."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        # 4 failures + 1 success = reset
        for _ in range(4):
            await circuit.record_failure()
        await circuit.record_success()
        assert circuit.state == CircuitState.CLOSED

        # Need 5 more consecutive failures to open
        for _ in range(5):
            await circuit.record_failure()
        assert circuit.state == CircuitState.OPEN


class TestCircuitBreakerRecoveryTimeout:
    """Test recovery timeout and retry timing."""

    @pytest.mark.asyncio
    async def test_circuit_blocks_before_timeout(self):
        """Circuit should block calls before recovery timeout."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=2)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        # Try to call immediately - should raise
        async def dummy_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await circuit.call(dummy_func)

        assert "temporarily unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_seconds_until_retry_calculation(self):
        """Circuit should correctly calculate seconds until retry."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=60)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        seconds = circuit._seconds_until_retry()
        assert 58 <= seconds <= 60  # Account for small time passage


class TestCircuitBreakerCallMethod:
    """Test circuit breaker call wrapping."""

    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Successful calls should work normally in CLOSED state."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        async def successful_func():
            return "result"

        result = await circuit.call(successful_func)
        assert result == "result"
        assert circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failed_call_records_failure(self):
        """Failed calls should record failure and re-raise exception."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        async def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError) as exc_info:
            await circuit.call(failing_func)

        assert "test error" in str(exc_info.value)
        assert circuit.failure_count == 1

    @pytest.mark.asyncio
    async def test_call_with_arguments(self):
        """Circuit should pass arguments to wrapped function."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await circuit.call(func_with_args, "x", "y", c="z")
        assert result == "x-y-z"


class TestCircuitBreakerConcurrency:
    """Test circuit breaker behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_failures(self):
        """Circuit should handle concurrent failure recording correctly."""
        circuit = CircuitBreaker(name="test", failure_threshold=5)

        async def record_failure_async():
            await circuit.record_failure()

        # Record 5 failures concurrently
        await asyncio.gather(*[record_failure_async() for _ in range(5)])

        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count >= 5

    @pytest.mark.asyncio
    async def test_concurrent_calls_when_open(self):
        """All concurrent calls should fail fast when circuit is OPEN."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=60)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        async def dummy_func():
            return "success"

        # Multiple concurrent calls should all raise CircuitBreakerOpenError
        tasks = [circuit.call(dummy_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            assert isinstance(result, CircuitBreakerOpenError)


class TestCircuitBreakerGetState:
    """Test circuit state reporting."""

    @pytest.mark.asyncio
    async def test_get_state_closed(self):
        """Get state should return correct info for CLOSED circuit."""
        circuit = CircuitBreaker(name="test-provider", failure_threshold=5)

        state = circuit.get_state()
        assert state["name"] == "test-provider"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["last_failure_time"] is None
        assert state["seconds_until_retry"] is None

    @pytest.mark.asyncio
    async def test_get_state_open(self):
        """Get state should return correct info for OPEN circuit."""
        circuit = CircuitBreaker(name="test-provider", failure_threshold=5, recovery_timeout=60)

        # Open the circuit
        for _ in range(5):
            await circuit.record_failure()

        state = circuit.get_state()
        assert state["name"] == "test-provider"
        assert state["state"] == "open"
        assert state["failure_count"] == 5
        assert state["last_failure_time"] is not None
        assert state["seconds_until_retry"] is not None
        assert state["seconds_until_retry"] > 0

    @pytest.mark.asyncio
    async def test_get_state_half_open(self):
        """Get state should return correct info for HALF_OPEN circuit."""
        circuit = CircuitBreaker(name="test-provider", failure_threshold=5)

        circuit.state = CircuitState.HALF_OPEN
        state = circuit.get_state()
        assert state["name"] == "test-provider"
        assert state["state"] == "half_open"


class TestCircuitBreakerConfiguration:
    """Test different circuit breaker configurations."""

    @pytest.mark.asyncio
    async def test_custom_failure_threshold(self):
        """Circuit should respect custom failure threshold."""
        circuit = CircuitBreaker(name="test", failure_threshold=3)

        for _ in range(3):
            await circuit.record_failure()

        assert circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_custom_success_threshold(self):
        """Circuit should require multiple successes if configured."""
        circuit = CircuitBreaker(name="test", failure_threshold=5, success_threshold=3)

        circuit.state = CircuitState.HALF_OPEN

        # First 2 successes shouldn't close circuit
        await circuit.record_success()
        assert circuit.state == CircuitState.HALF_OPEN
        await circuit.record_success()
        assert circuit.state == CircuitState.HALF_OPEN

        # Third success should close it
        await circuit.record_success()
        assert circuit.state == CircuitState.CLOSED
