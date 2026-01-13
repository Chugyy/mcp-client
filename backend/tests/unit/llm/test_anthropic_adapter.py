"""Unit tests for Anthropic LLM adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from app.core.services.llm.adapters.anthropic import AnthropicAdapter
from app.core.services.llm.types import ToolDefinition, ToolCall


class AsyncContextManagerMock:
    """Helper class to create async context manager mocks."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic SDK client."""
    client = AsyncMock()
    return client


@pytest.fixture
def anthropic_adapter(mock_anthropic_client):
    """Create Anthropic adapter with mocked client."""
    with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
        mock_client_class.return_value = mock_anthropic_client
        adapter = AnthropicAdapter(api_key="test-key")
        adapter.client = mock_anthropic_client
        return adapter


class TestAnthropicAdapterStream:
    """Tests for streaming message creation."""

    @pytest.mark.asyncio
    async def test_stream_success(self, anthropic_adapter, mock_anthropic_client):
        """Test successful streaming message creation."""
        # Mock streaming response
        async def mock_text_stream():
            yield "Hello"
            yield " "
            yield "world"
            yield "!"

        mock_stream = MagicMock()
        mock_stream.text_stream = mock_text_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        # Stream messages
        chunks = []
        async for chunk in anthropic_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4",
            max_tokens=1024
        ):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "world", "!"]
        mock_anthropic_client.messages.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_with_system_prompt(self, anthropic_adapter, mock_anthropic_client):
        """Test streaming with system prompt parameter."""
        # Mock streaming response
        async def mock_text_stream():
            yield "Response"

        mock_stream = MagicMock()
        mock_stream.text_stream = mock_text_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        # Stream with system prompt
        chunks = []
        async for chunk in anthropic_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4",
            max_tokens=1024,
            system="You are a helpful assistant"
        ):
            chunks.append(chunk)

        # Verify system parameter was passed correctly
        call_kwargs = mock_anthropic_client.messages.stream.call_args[1]
        assert "system" in call_kwargs
        assert call_kwargs["system"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_stream_default_max_tokens(self, anthropic_adapter, mock_anthropic_client):
        """Test streaming applies default max_tokens if not provided."""
        async def mock_text_stream():
            yield "Test"

        mock_stream = MagicMock()
        mock_stream.text_stream = mock_text_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        # Stream without max_tokens
        chunks = []
        async for chunk in anthropic_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4"
        ):
            chunks.append(chunk)

        # Verify max_tokens was set
        call_kwargs = mock_anthropic_client.messages.stream.call_args[1]
        assert "max_tokens" in call_kwargs


class TestAnthropicAdapterRetry:
    """Tests for retry logic on errors."""

    @pytest.mark.asyncio
    async def test_stream_rate_limit_retry_success(self, anthropic_adapter, mock_anthropic_client):
        """Test rate limit error triggers retry and eventually succeeds."""
        # First attempt: rate limit error
        # Second attempt: success
        attempt_count = 0

        def mock_stream_factory(**kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                # First attempt fails with rate limit
                raise Exception("Rate limit exceeded")
            else:
                # Second attempt succeeds
                async def mock_text_stream():
                    yield "Success"

                mock_stream = MagicMock()
                mock_stream.text_stream = mock_text_stream()
                return AsyncContextManagerMock(mock_stream)

        # Mock is_retriable_error to return True for first error
        anthropic_adapter.is_retriable_error = MagicMock(return_value=True)

        mock_anthropic_client.messages.stream = mock_stream_factory

        # Should retry and succeed
        chunks = []
        async for chunk in anthropic_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4",
            max_tokens=1024
        ):
            chunks.append(chunk)

        assert chunks == ["Success"]
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_stream_rate_limit_max_retries_exceeded(self, anthropic_adapter, mock_anthropic_client):
        """Test rate limit error fails after max retries."""
        # Mock rate limit error
        rate_limit_error = Exception("Rate limit exceeded")
        rate_limit_error.status_code = 429

        def failing_stream(**kwargs):
            raise rate_limit_error

        mock_anthropic_client.messages.stream = failing_stream

        # Should fail after 3 attempts
        with pytest.raises(Exception, match="Rate limit exceeded"):
            async for chunk in anthropic_adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_non_retriable_error_immediate_fail(self, anthropic_adapter, mock_anthropic_client):
        """Test non-retriable error fails immediately without retry."""
        # Mock non-retriable error (400 Bad Request)
        bad_request_error = Exception("Invalid request")
        bad_request_error.status_code = 400

        def failing_stream(**kwargs):
            raise bad_request_error

        mock_anthropic_client.messages.stream = failing_stream

        # Should fail immediately
        with pytest.raises(Exception, match="Invalid request"):
            async for chunk in anthropic_adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                pass


class TestAnthropicAdapterToolUse:
    """Tests for tool use (function calling)."""

    @pytest.mark.asyncio
    async def test_stream_with_tools_text_only(self, anthropic_adapter, mock_anthropic_client):
        """Test streaming with tools but only text response."""
        # Mock events: text deltas only
        async def mock_event_stream():
            # Text delta events
            event1 = MagicMock()
            event1.type = "content_block_delta"
            event1.delta = MagicMock()
            event1.delta.type = "text_delta"
            event1.delta.text = "Hello"
            yield event1

            event2 = MagicMock()
            event2.type = "content_block_delta"
            event2.delta = MagicMock()
            event2.delta.type = "text_delta"
            event2.delta.text = " world"
            yield event2

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                input_schema={"type": "object", "properties": {}},
                server_id="test-server"
            )
        ]

        chunks = []
        async for chunk in anthropic_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            tools=tools,
            model="claude-sonnet-4",
            max_tokens=1024
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"

    @pytest.mark.asyncio
    async def test_stream_with_tools_tool_call(self, anthropic_adapter, mock_anthropic_client):
        """Test streaming with tool call detection."""
        # Mock events: tool_use block
        async def mock_event_stream():
            # Start tool_use block
            event1 = MagicMock()
            event1.type = "content_block_start"
            event1.content_block = MagicMock()
            event1.content_block.type = "tool_use"
            event1.content_block.id = "call_123"
            event1.content_block.name = "test_tool"
            yield event1

            # Input JSON delta
            event2 = MagicMock()
            event2.type = "content_block_delta"
            event2.delta = MagicMock()
            event2.delta.type = "input_json_delta"
            event2.delta.partial_json = '{"param": '
            yield event2

            event3 = MagicMock()
            event3.type = "content_block_delta"
            event3.delta = MagicMock()
            event3.delta.type = "input_json_delta"
            event3.delta.partial_json = '"value"}'
            yield event3

            # End tool_use block
            event4 = MagicMock()
            event4.type = "content_block_stop"
            yield event4

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
                server_id="test-server"
            )
        ]

        chunks = []
        async for chunk in anthropic_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Use tool"}],
            tools=tools,
            model="claude-sonnet-4",
            max_tokens=1024
        ):
            chunks.append(chunk)

        # Should have one ToolCall
        assert len(chunks) == 1
        assert isinstance(chunks[0], ToolCall)
        assert chunks[0].id == "call_123"
        assert chunks[0].name == "test_tool"
        assert chunks[0].arguments == {"param": "value"}

    @pytest.mark.asyncio
    async def test_stream_with_tools_invalid_json(self, anthropic_adapter, mock_anthropic_client):
        """Test tool call with invalid JSON arguments falls back to empty dict."""
        # Mock events: tool_use with invalid JSON
        async def mock_event_stream():
            # Start tool_use block
            event1 = MagicMock()
            event1.type = "content_block_start"
            event1.content_block = MagicMock()
            event1.content_block.type = "tool_use"
            event1.content_block.id = "call_456"
            event1.content_block.name = "broken_tool"
            yield event1

            # Invalid JSON
            event2 = MagicMock()
            event2.type = "content_block_delta"
            event2.delta = MagicMock()
            event2.delta.type = "input_json_delta"
            event2.delta.partial_json = '{invalid json'
            yield event2

            # End block
            event3 = MagicMock()
            event3.type = "content_block_stop"
            yield event3

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()

        mock_anthropic_client.messages.stream = MagicMock(return_value=AsyncContextManagerMock(mock_stream))

        tools = [
            ToolDefinition(
                name="broken_tool",
                description="A tool",
                input_schema={"type": "object", "properties": {}},
                server_id="test-server"
            )
        ]

        chunks = []
        async for chunk in anthropic_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Use tool"}],
            tools=tools,
            model="claude-sonnet-4",
            max_tokens=1024
        ):
            chunks.append(chunk)

        # Should still create ToolCall with empty arguments
        assert len(chunks) == 1
        assert isinstance(chunks[0], ToolCall)
        assert chunks[0].arguments == {}


class TestAnthropicAdapterModels:
    """Tests for model listing."""

    @pytest.mark.asyncio
    async def test_list_models_success(self, anthropic_adapter, mock_anthropic_client):
        """Test successful model listing."""
        # Mock API response
        mock_model = MagicMock()
        mock_model.id = "claude-sonnet-4"
        mock_model.type = "model"
        mock_model.display_name = "Claude Sonnet 4"
        mock_model.created_at = "2024-01-01T00:00:00Z"

        mock_response = MagicMock()
        mock_response.data = [mock_model]

        mock_anthropic_client.models.list.return_value = mock_response

        models = await anthropic_adapter.list_models()

        assert len(models) == 1
        assert models[0]["id"] == "claude-sonnet-4"
        assert models[0]["type"] == "model"
        assert models[0]["display_name"] == "Claude Sonnet 4"
        assert models[0]["provider"] == "Anthropic"

    @pytest.mark.asyncio
    async def test_list_models_fallback_on_error(self, anthropic_adapter, mock_anthropic_client):
        """Test fallback to hardcoded list on API error."""
        # Mock API error
        mock_anthropic_client.models.list.side_effect = Exception("API error")

        models = await anthropic_adapter.list_models()

        # Should return hardcoded fallback list
        assert len(models) > 0
        assert any(m["id"] == "claude-sonnet-4-5-20250929" for m in models)
        assert all(m["provider"] == "Anthropic" for m in models)


class TestAnthropicAdapterErrorHandling:
    """Tests for error classification."""

    def test_is_retriable_error_429(self, anthropic_adapter):
        """Test 429 rate limit is retriable."""
        error = Exception("Rate limit")
        error.status_code = 429

        assert anthropic_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_500(self, anthropic_adapter):
        """Test 500 server error is retriable."""
        error = Exception("Server error")
        error.status_code = 500

        assert anthropic_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_503(self, anthropic_adapter):
        """Test 503 service unavailable is retriable."""
        error = Exception("Service unavailable")
        error.status_code = 503

        assert anthropic_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_529(self, anthropic_adapter):
        """Test 529 overloaded is retriable."""
        error = Exception("Overloaded")
        error.status_code = 529

        assert anthropic_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_400(self, anthropic_adapter):
        """Test 400 bad request is NOT retriable."""
        error = Exception("Bad request")
        error.status_code = 400

        assert anthropic_adapter.is_retriable_error(error) is False

    def test_is_retriable_error_401(self, anthropic_adapter):
        """Test 401 unauthorized is NOT retriable."""
        error = Exception("Unauthorized")
        error.status_code = 401

        assert anthropic_adapter.is_retriable_error(error) is False


class TestAnthropicAdapterMessageTransform:
    """Tests for message transformation."""

    def test_transform_messages_with_system_prompt(self, anthropic_adapter):
        """Test messages transformed with system prompt in extra_params."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        system_prompt = "You are helpful"

        transformed_messages, extra_params = anthropic_adapter.transform_messages(
            messages, system_prompt
        )

        # System should be in extra_params, not messages
        assert "system" in extra_params
        assert extra_params["system"] == "You are helpful"
        assert len(transformed_messages) == 1
        assert transformed_messages[0]["role"] == "user"

    def test_transform_messages_without_system_prompt(self, anthropic_adapter):
        """Test messages transformed without system prompt."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]

        transformed_messages, extra_params = anthropic_adapter.transform_messages(
            messages, None
        )

        # No system in extra_params
        assert "system" not in extra_params or extra_params["system"] is None
        assert len(transformed_messages) == 1

    def test_transform_messages_filters_system_role(self, anthropic_adapter):
        """Test system role messages are filtered from message list."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Hello"}
        ]

        transformed_messages, extra_params = anthropic_adapter.transform_messages(
            messages, None
        )

        # System role should be filtered out
        assert len(transformed_messages) == 1
        assert transformed_messages[0]["role"] == "user"
