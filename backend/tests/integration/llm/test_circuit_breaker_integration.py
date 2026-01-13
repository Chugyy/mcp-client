#!/usr/bin/env python3
# tests/integration/llm/test_circuit_breaker_integration.py
"""Integration tests for circuit breaker with LLM gateway."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.llm.gateway import LLMGateway
from app.core.utils.circuit_breaker import CircuitState
from app.core.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerGatewayIntegration:
    """Test circuit breaker integration with LLM gateway."""

    @pytest.fixture
    def gateway(self):
        """Create a fresh LLM gateway instance for each test."""
        return LLMGateway()

    @pytest.mark.asyncio
    async def test_gateway_has_circuit_breakers(self, gateway):
        """Gateway should initialize circuit breakers for each provider."""
        assert "anthropic" in gateway.circuit_breakers
        assert "openai" in gateway.circuit_breakers
        assert gateway.circuit_breakers["anthropic"].name == "anthropic"
        assert gateway.circuit_breakers["openai"].name == "openai"

    @pytest.mark.asyncio
    async def test_circuit_breakers_start_closed(self, gateway):
        """All circuit breakers should start in CLOSED state."""
        for circuit in gateway.circuit_breakers.values():
            assert circuit.state == CircuitState.CLOSED
            assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_stream_fails_fast_when_circuit_open(self, gateway):
        """Stream should fail fast when circuit breaker is open."""
        # Open the anthropic circuit
        anthropic_circuit = gateway.circuit_breakers["anthropic"]
        for _ in range(5):
            await anthropic_circuit.record_failure()

        assert anthropic_circuit.state == CircuitState.OPEN

        # Try to stream with anthropic - should fail immediately
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async for _ in gateway.stream(
                messages=[{"role": "user", "content": "test"}],
                model="claude-sonnet-4-5-20250929"
            ):
                pass

        assert "temporarily unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_provider_independence(self, gateway):
        """One provider's circuit shouldn't affect another provider."""
        # Open anthropic circuit
        anthropic_circuit = gateway.circuit_breakers["anthropic"]
        for _ in range(5):
            await anthropic_circuit.record_failure()

        assert anthropic_circuit.state == CircuitState.OPEN

        # OpenAI circuit should still be closed
        openai_circuit = gateway.circuit_breakers["openai"]
        assert openai_circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_stream_failures(self, gateway):
        """Circuit should open after repeated stream failures."""
        # Mock the router to always fail
        async def failing_stream(*args, **kwargs):
            raise Exception("Provider error")
            yield  # Make it a generator

        gateway.router.stream_with_retry = failing_stream

        # Try to stream 5 times with anthropic
        for i in range(5):
            try:
                async for _ in gateway.stream(
                    messages=[{"role": "user", "content": "test"}],
                    model="claude-sonnet-4-5-20250929"
                ):
                    pass
            except Exception:
                pass  # Expected to fail

        # Circuit should now be open
        anthropic_circuit = gateway.circuit_breakers["anthropic"]
        assert anthropic_circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_recovery_after_timeout(self, gateway):
        """Circuit should attempt recovery after timeout."""
        # Create circuit with short recovery timeout for testing
        gateway.circuit_breakers["anthropic"].recovery_timeout = 1

        # Open the circuit
        for _ in range(5):
            await gateway.circuit_breakers["anthropic"].record_failure()

        assert gateway.circuit_breakers["anthropic"].state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Mock successful stream
        async def successful_stream(*args, **kwargs):
            yield "chunk1"
            yield "chunk2"

        gateway.router.stream_with_retry = successful_stream

        # Stream should work now (circuit transitions to HALF_OPEN then CLOSED)
        chunks = []
        async for chunk in gateway.stream(
            messages=[{"role": "user", "content": "test"}],
            model="claude-sonnet-4-5-20250929"
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert gateway.circuit_breakers["anthropic"].state == CircuitState.CLOSED


class TestCircuitBreakerHealthEndpoint:
    """Test health check endpoint integration."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_all_circuits(self):
        """Health endpoint should return status of all circuit breakers."""
        from app.api.v1.routes.health import get_circuit_breaker_status

        response = await get_circuit_breaker_status()
        content = response.body.decode()

        assert response.status_code == 200
        assert "anthropic" in content
        assert "openai" in content
        assert "closed" in content

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_503_when_circuit_open(self):
        """Health endpoint should return 503 when any circuit is open."""
        from app.api.v1.routes.health import get_circuit_breaker_status
        from app.core.services.llm.gateway import llm_gateway

        # Open one circuit
        for _ in range(5):
            await llm_gateway.circuit_breakers["anthropic"].record_failure()

        response = await get_circuit_breaker_status()

        assert response.status_code == 503
        content = response.body.decode()
        assert "degraded" in content

        # Clean up - reset circuit
        llm_gateway.circuit_breakers["anthropic"].state = CircuitState.CLOSED
        llm_gateway.circuit_breakers["anthropic"].failure_count = 0

    @pytest.mark.asyncio
    async def test_health_endpoint_shows_seconds_until_retry(self):
        """Health endpoint should show retry countdown for open circuits."""
        from app.api.v1.routes.health import get_circuit_breaker_status
        from app.core.services.llm.gateway import llm_gateway

        # Open circuit
        for _ in range(5):
            await llm_gateway.circuit_breakers["anthropic"].record_failure()

        response = await get_circuit_breaker_status()
        content = response.body.decode()

        assert "seconds_until_retry" in content
        assert response.status_code == 503

        # Clean up
        llm_gateway.circuit_breakers["anthropic"].state = CircuitState.CLOSED
        llm_gateway.circuit_breakers["anthropic"].failure_count = 0


class TestCircuitBreakerWithToolCalling:
    """Test circuit breaker with stream_with_tools method."""

    @pytest.fixture
    def gateway(self):
        """Create a fresh LLM gateway instance."""
        return LLMGateway()

    @pytest.mark.asyncio
    async def test_stream_with_tools_respects_circuit_breaker(self, gateway):
        """stream_with_tools should respect circuit breaker state."""
        # Open the circuit
        for _ in range(5):
            await gateway.circuit_breakers["anthropic"].record_failure()

        assert gateway.circuit_breakers["anthropic"].state == CircuitState.OPEN

        # Try to stream with tools - should fail fast
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async for _ in gateway.stream_with_tools(
                messages=[{"role": "user", "content": "test"}],
                model="claude-sonnet-4-5-20250929",
                tools=[]
            ):
                pass

        assert "temporarily unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_stream_with_tools_records_success(self, gateway):
        """stream_with_tools should record success on completion."""
        # Mock adapter to return successful stream
        async def mock_stream_with_tools(*args, **kwargs):
            yield "text chunk"
            # No tool calls, so streaming should complete

        # Mock the adapter
        with patch.object(gateway, '_get_adapter_for_provider') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.stream_with_tools = mock_stream_with_tools
            mock_adapter.transform_messages = MagicMock(return_value=([], {}))
            mock_get_adapter.return_value = mock_adapter

            # Stream should complete successfully
            chunks = []
            async for chunk in gateway.stream_with_tools(
                messages=[{"role": "user", "content": "test"}],
                model="claude-sonnet-4-5-20250929",
                tools=[]
            ):
                chunks.append(chunk)

            # Circuit should record success
            circuit = gateway.circuit_breakers["anthropic"]
            assert circuit.failure_count == 0


class TestCircuitBreakerConfiguration:
    """Test circuit breaker configuration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_default_configuration(self):
        """Circuit breakers should have correct default configuration."""
        gateway = LLMGateway()

        for circuit in gateway.circuit_breakers.values():
            assert circuit.failure_threshold == 5
            assert circuit.recovery_timeout == 60
            assert circuit.success_threshold == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_per_provider_instances(self):
        """Each provider should have independent circuit breaker instance."""
        gateway = LLMGateway()

        anthropic_circuit = gateway.circuit_breakers["anthropic"]
        openai_circuit = gateway.circuit_breakers["openai"]

        # They should be different instances
        assert anthropic_circuit is not openai_circuit

        # Modifying one shouldn't affect the other
        await anthropic_circuit.record_failure()
        assert anthropic_circuit.failure_count == 1
        assert openai_circuit.failure_count == 0
