"""Unit tests for LLM retry logic (Router)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.core.services.llm.utils.router import Router
from app.core.services.llm.adapters.base import BaseAdapter


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.stream_calls = 0
        self.should_fail = False
        self.fail_count = 0
        self.retriable = True

    async def stream(self, messages, **params):
        """Mock stream method."""
        self.stream_calls += 1

        if self.should_fail and self.stream_calls <= self.fail_count:
            if self.retriable:
                error = Exception("Retriable error")
                error.status_code = 429
            else:
                error = Exception("Non-retriable error")
                error.status_code = 400
            raise error

        # Success
        yield "Success"
        yield " chunk"

    def is_retriable_error(self, exception):
        """Mock retriable error check."""
        return getattr(exception, 'status_code', None) in [429, 500, 502, 503, 504]

    async def list_models(self):
        """Mock list models."""
        return []

    async def stream_with_tools(self, messages, tools, **params):
        """Mock stream with tools."""
        yield "tool response"


class TestRouterInitialization:
    """Tests for Router initialization."""

    def test_router_default_max_retries(self):
        """Test router initializes with default max retries."""
        router = Router()
        assert router.max_retries == 3

    def test_router_custom_max_retries(self):
        """Test router initializes with custom max retries."""
        router = Router(max_retries=5)
        assert router.max_retries == 5


class TestRouterRetrySuccess:
    """Tests for successful retry scenarios."""

    @pytest.mark.asyncio
    async def test_stream_success_first_attempt(self):
        """Test streaming succeeds on first attempt."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        assert chunks == ["Success", " chunk"]
        assert adapter.stream_calls == 1

    @pytest.mark.asyncio
    async def test_stream_success_on_second_attempt(self):
        """Test streaming succeeds on second attempt after retriable error."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Fail once, then succeed
        adapter.should_fail = True
        adapter.fail_count = 1
        adapter.retriable = True

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        assert chunks == ["Success", " chunk"]
        assert adapter.stream_calls == 2

    @pytest.mark.asyncio
    async def test_stream_success_on_third_attempt(self):
        """Test streaming succeeds on third attempt after two retriable errors."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Fail twice, then succeed
        adapter.should_fail = True
        adapter.fail_count = 2
        adapter.retriable = True

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        assert chunks == ["Success", " chunk"]
        assert adapter.stream_calls == 3


class TestRouterRetryFailure:
    """Tests for retry failure scenarios."""

    @pytest.mark.asyncio
    async def test_stream_fails_after_max_retries(self):
        """Test streaming fails after max retries exceeded."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Always fail with retriable error
        adapter.should_fail = True
        adapter.fail_count = 10
        adapter.retriable = True

        with pytest.raises(Exception, match="Retriable error"):
            async for chunk in router.stream_with_retry(
                adapter,
                messages=[{"role": "user", "content": "Hello"}],
                params={"model": "test-model"}
            ):
                pass

        # Should have tried 3 times
        assert adapter.stream_calls == 3

    @pytest.mark.asyncio
    async def test_stream_fails_immediately_on_non_retriable_error(self):
        """Test streaming fails immediately on non-retriable error."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Fail with non-retriable error
        adapter.should_fail = True
        adapter.fail_count = 1
        adapter.retriable = False

        with pytest.raises(Exception, match="Non-retriable error"):
            async for chunk in router.stream_with_retry(
                adapter,
                messages=[{"role": "user", "content": "Hello"}],
                params={"model": "test-model"}
            ):
                pass

        # Should have tried only once
        assert adapter.stream_calls == 1


class TestRouterExponentialBackoff:
    """Tests for exponential backoff timing."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test retry uses exponential backoff (2^attempt seconds)."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Fail twice, succeed on third
        adapter.should_fail = True
        adapter.fail_count = 2
        adapter.retriable = True

        start_time = asyncio.get_event_loop().time()

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        # Should have waited 2^0=1s + 2^1=2s = 3s minimum
        # Adding some tolerance for test execution time
        assert elapsed >= 3.0
        assert elapsed < 5.0  # Should not wait too long


class TestRouterRetryAttemptLogging:
    """Tests for retry attempt tracking."""

    @pytest.mark.asyncio
    async def test_retry_attempt_counter(self):
        """Test retry attempts are counted correctly."""
        router = Router(max_retries=5)
        adapter = MockAdapter(api_key="test")

        # Fail 3 times, succeed on 4th
        adapter.should_fail = True
        adapter.fail_count = 3
        adapter.retriable = True

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        # Should have made 4 attempts total
        assert adapter.stream_calls == 4


class TestRouterEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_max_retries_zero(self):
        """Test router with max_retries=0 does not attempt any retries."""
        router = Router(max_retries=0)
        adapter = MockAdapter(api_key="test")

        # Should fail immediately even with retriable error
        adapter.should_fail = True
        adapter.fail_count = 1
        adapter.retriable = True

        # With max_retries=0, range(0) = [], so stream is never called
        # Should return empty generator (no chunks)
        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        # Should have no chunks since no attempts were made
        assert len(chunks) == 0
        assert adapter.stream_calls == 0

    @pytest.mark.asyncio
    async def test_max_retries_one(self):
        """Test router with max_retries=1 tries only once."""
        router = Router(max_retries=1)
        adapter = MockAdapter(api_key="test")

        adapter.should_fail = True
        adapter.fail_count = 10
        adapter.retriable = True

        with pytest.raises(Exception, match="Retriable error"):
            async for chunk in router.stream_with_retry(
                adapter,
                messages=[{"role": "user", "content": "Hello"}],
                params={"model": "test-model"}
            ):
                pass

        # Should try only once
        assert adapter.stream_calls == 1

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Test router handles empty messages list."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        # Should still work
        assert chunks == ["Success", " chunk"]

    @pytest.mark.asyncio
    async def test_empty_params(self):
        """Test router handles empty params dict."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={}
        ):
            chunks.append(chunk)

        # Should still work
        assert chunks == ["Success", " chunk"]


class TestRouterIntegrationWithAdapter:
    """Tests for router integration with adapter error checking."""

    @pytest.mark.asyncio
    async def test_router_respects_adapter_is_retriable_error(self):
        """Test router uses adapter's is_retriable_error method."""
        router = Router(max_retries=3)

        # Create adapter that says 429 is NOT retriable
        adapter = MockAdapter(api_key="test")
        adapter.is_retriable_error = MagicMock(return_value=False)

        adapter.should_fail = True
        adapter.fail_count = 1

        # Should fail immediately because adapter says error is not retriable
        with pytest.raises(Exception):
            async for chunk in router.stream_with_retry(
                adapter,
                messages=[{"role": "user", "content": "Hello"}],
                params={"model": "test-model"}
            ):
                pass

        # Should only try once
        assert adapter.stream_calls == 1
        # Should have called is_retriable_error
        adapter.is_retriable_error.assert_called()

    @pytest.mark.asyncio
    async def test_router_uses_different_adapters(self):
        """Test router can work with different adapter instances."""
        router = Router(max_retries=3)

        adapter1 = MockAdapter(api_key="key1")
        adapter2 = MockAdapter(api_key="key2")

        # Use adapter1
        chunks1 = []
        async for chunk in router.stream_with_retry(
            adapter1,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "model1"}
        ):
            chunks1.append(chunk)

        # Use adapter2
        chunks2 = []
        async for chunk in router.stream_with_retry(
            adapter2,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "model2"}
        ):
            chunks2.append(chunk)

        # Both should work independently
        assert chunks1 == ["Success", " chunk"]
        assert chunks2 == ["Success", " chunk"]
        assert adapter1.stream_calls == 1
        assert adapter2.stream_calls == 1


class TestRouterRetryLimits:
    """Tests for retry limit enforcement."""

    @pytest.mark.asyncio
    async def test_max_retry_limit_enforced(self):
        """Test max retry limit is strictly enforced."""
        router = Router(max_retries=3)
        adapter = MockAdapter(api_key="test")

        # Always fail
        adapter.should_fail = True
        adapter.fail_count = 100
        adapter.retriable = True

        with pytest.raises(Exception):
            async for chunk in router.stream_with_retry(
                adapter,
                messages=[{"role": "user", "content": "Hello"}],
                params={"model": "test-model"}
            ):
                pass

        # Should have tried exactly max_retries times
        assert adapter.stream_calls == 3

    @pytest.mark.asyncio
    async def test_success_stops_retrying(self):
        """Test success stops retry loop even if retries remaining."""
        router = Router(max_retries=10)
        adapter = MockAdapter(api_key="test")

        # Fail once, succeed on second attempt
        adapter.should_fail = True
        adapter.fail_count = 1
        adapter.retriable = True

        chunks = []
        async for chunk in router.stream_with_retry(
            adapter,
            messages=[{"role": "user", "content": "Hello"}],
            params={"model": "test-model"}
        ):
            chunks.append(chunk)

        # Should stop after success (2 attempts), not continue to max_retries
        assert adapter.stream_calls == 2
        assert chunks == ["Success", " chunk"]
