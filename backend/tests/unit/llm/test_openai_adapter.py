"""Unit tests for OpenAI LLM adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.services.llm.adapters.openai import OpenAIAdapter, generate_display_name
from app.core.services.llm.types import ToolDefinition, ToolCall


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI SDK client."""
    client = AsyncMock()
    return client


@pytest.fixture
def openai_adapter(mock_openai_client):
    """Create OpenAI adapter with mocked client."""
    with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
        mock_client_class.return_value = mock_openai_client
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_openai_client
        return adapter


class TestDisplayNameGeneration:
    """Tests for display name generation utility."""

    def test_generate_display_name_gpt4o(self):
        """Test GPT-4O display name generation."""
        assert generate_display_name("gpt-4o") == "GPT 4O"

    def test_generate_display_name_gpt4o_mini(self):
        """Test GPT-4O Mini display name generation."""
        assert generate_display_name("gpt-4o-mini") == "GPT 4O Mini"

    def test_generate_display_name_gpt35_turbo(self):
        """Test GPT-3.5 Turbo display name generation."""
        assert generate_display_name("gpt-3.5-turbo") == "GPT 3.5 Turbo"

    def test_generate_display_name_gpt4_turbo_preview(self):
        """Test GPT-4 Turbo Preview display name generation."""
        assert generate_display_name("gpt-4-turbo-preview") == "GPT 4 Turbo Preview"

    def test_generate_display_name_fine_tuned(self):
        """Test fine-tuned model keeps original format."""
        model_id = "ft:gpt-3.5-turbo:company:custom:12345"
        assert generate_display_name(model_id) == model_id


class TestOpenAIAdapterStream:
    """Tests for streaming chat completion."""

    @pytest.mark.asyncio
    async def test_stream_success(self, openai_adapter, mock_openai_client):
        """Test successful streaming chat completion."""
        # Mock streaming response
        async def mock_stream():
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta = MagicMock()
            chunk1.choices[0].delta.content = "Hello"
            yield chunk1

            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            chunk2.choices[0].delta.content = " world"
            yield chunk2

            chunk3 = MagicMock()
            chunk3.choices = [MagicMock()]
            chunk3.choices[0].delta = MagicMock()
            chunk3.choices[0].delta.content = "!"
            yield chunk3

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        # Stream messages
        chunks = []
        async for chunk in openai_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini"
        ):
            chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_with_empty_deltas(self, openai_adapter, mock_openai_client):
        """Test streaming handles chunks with no content."""
        # Mock streaming with some empty deltas
        async def mock_stream():
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta = MagicMock()
            chunk1.choices[0].delta.content = None  # Empty delta
            yield chunk1

            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            chunk2.choices[0].delta.content = "Text"
            yield chunk2

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in openai_adapter.stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini"
        ):
            chunks.append(chunk)

        # Should only yield non-None content
        assert chunks == ["Text"]

    @pytest.mark.asyncio
    async def test_stream_error(self, openai_adapter, mock_openai_client):
        """Test streaming handles errors properly."""
        # Mock error
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with pytest.raises(Exception, match="API error"):
            async for chunk in openai_adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4o-mini"
            ):
                pass


class TestOpenAIAdapterToolUse:
    """Tests for function calling (tools)."""

    @pytest.mark.asyncio
    async def test_stream_with_tools_text_only(self, openai_adapter, mock_openai_client):
        """Test streaming with tools but only text response."""
        # Mock streaming with text deltas only
        async def mock_stream():
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta = MagicMock()
            chunk1.choices[0].delta.content = "Hello"
            chunk1.choices[0].delta.tool_calls = None
            chunk1.choices[0].finish_reason = None
            yield chunk1

            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            chunk2.choices[0].delta.content = " world"
            chunk2.choices[0].delta.tool_calls = None
            chunk2.choices[0].finish_reason = None
            yield chunk2

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                input_schema={"type": "object", "properties": {}},
                server_id="test-server"
            )
        ]

        chunks = []
        async for chunk in openai_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            tools=tools,
            model="gpt-4o-mini"
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"

    @pytest.mark.asyncio
    async def test_stream_with_tools_tool_call(self, openai_adapter, mock_openai_client):
        """Test streaming with tool call detection."""
        # Mock streaming with tool calls
        async def mock_stream():
            # First chunk: start tool call
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta = MagicMock()
            chunk1.choices[0].delta.content = None

            tool_call_delta = MagicMock()
            tool_call_delta.index = 0
            tool_call_delta.id = "call_123"
            tool_call_delta.function = MagicMock()
            tool_call_delta.function.name = "test_tool"
            tool_call_delta.function.arguments = ""

            chunk1.choices[0].delta.tool_calls = [tool_call_delta]
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Second chunk: arguments part 1
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            chunk2.choices[0].delta.content = None

            tool_call_delta2 = MagicMock()
            tool_call_delta2.index = 0
            tool_call_delta2.id = None
            tool_call_delta2.function = MagicMock()
            tool_call_delta2.function.name = None
            tool_call_delta2.function.arguments = '{"param": '

            chunk2.choices[0].delta.tool_calls = [tool_call_delta2]
            chunk2.choices[0].finish_reason = None
            yield chunk2

            # Third chunk: arguments part 2
            chunk3 = MagicMock()
            chunk3.choices = [MagicMock()]
            chunk3.choices[0].delta = MagicMock()
            chunk3.choices[0].delta.content = None

            tool_call_delta3 = MagicMock()
            tool_call_delta3.index = 0
            tool_call_delta3.id = None
            tool_call_delta3.function = MagicMock()
            tool_call_delta3.function.name = None
            tool_call_delta3.function.arguments = '"value"}'

            chunk3.choices[0].delta.tool_calls = [tool_call_delta3]
            chunk3.choices[0].finish_reason = None
            yield chunk3

            # Final chunk: finish
            chunk4 = MagicMock()
            chunk4.choices = [MagicMock()]
            chunk4.choices[0].delta = MagicMock()
            chunk4.choices[0].delta.content = None
            chunk4.choices[0].delta.tool_calls = None
            chunk4.choices[0].finish_reason = "tool_calls"
            yield chunk4

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
                server_id="test-server"
            )
        ]

        chunks = []
        async for chunk in openai_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Use tool"}],
            tools=tools,
            model="gpt-4o-mini"
        ):
            chunks.append(chunk)

        # Should have one ToolCall
        assert len(chunks) == 1
        assert isinstance(chunks[0], ToolCall)
        assert chunks[0].id == "call_123"
        assert chunks[0].name == "test_tool"
        assert chunks[0].arguments == {"param": "value"}

    @pytest.mark.asyncio
    async def test_stream_with_tools_multiple_calls(self, openai_adapter, mock_openai_client):
        """Test streaming with multiple tool calls."""
        # Mock streaming with 2 tool calls
        async def mock_stream():
            # Tool call 1
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta = MagicMock()
            chunk1.choices[0].delta.content = None

            tc1 = MagicMock()
            tc1.index = 0
            tc1.id = "call_1"
            tc1.function = MagicMock()
            tc1.function.name = "tool_one"
            tc1.function.arguments = '{"a": 1}'

            chunk1.choices[0].delta.tool_calls = [tc1]
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Tool call 2
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            chunk2.choices[0].delta.content = None

            tc2 = MagicMock()
            tc2.index = 1
            tc2.id = "call_2"
            tc2.function = MagicMock()
            tc2.function.name = "tool_two"
            tc2.function.arguments = '{"b": 2}'

            chunk2.choices[0].delta.tool_calls = [tc2]
            chunk2.choices[0].finish_reason = None
            yield chunk2

            # Finish
            chunk3 = MagicMock()
            chunk3.choices = [MagicMock()]
            chunk3.choices[0].delta = MagicMock()
            chunk3.choices[0].delta.content = None
            chunk3.choices[0].delta.tool_calls = None
            chunk3.choices[0].finish_reason = "tool_calls"
            yield chunk3

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        tools = [
            ToolDefinition(name="tool_one", description="Tool 1", input_schema={}, server_id="s1"),
            ToolDefinition(name="tool_two", description="Tool 2", input_schema={}, server_id="s2")
        ]

        chunks = []
        async for chunk in openai_adapter.stream_with_tools(
            messages=[{"role": "user", "content": "Use tools"}],
            tools=tools,
            model="gpt-4o-mini"
        ):
            chunks.append(chunk)

        # Should have 2 ToolCalls
        assert len(chunks) == 2
        assert all(isinstance(c, ToolCall) for c in chunks)
        assert chunks[0].name == "tool_one"
        assert chunks[1].name == "tool_two"


class TestOpenAIAdapterModels:
    """Tests for model listing."""

    @pytest.mark.asyncio
    async def test_list_models_success(self, openai_adapter, mock_openai_client):
        """Test successful model listing."""
        # Mock model objects
        mock_model1 = MagicMock()
        mock_model1.id = "gpt-4o"
        mock_model1.object = "model"
        mock_model1.created = 1234567890
        mock_model1.owned_by = "openai"

        mock_model2 = MagicMock()
        mock_model2.id = "gpt-3.5-turbo"
        mock_model2.object = "model"
        mock_model2.created = 1234567891
        mock_model2.owned_by = "openai"

        # Mock models that should be filtered out
        mock_model3 = MagicMock()
        mock_model3.id = "text-embedding-ada-002"
        mock_model3.object = "model"
        mock_model3.created = 1234567892
        mock_model3.owned_by = "openai"

        async def mock_list():
            yield mock_model1
            yield mock_model2
            yield mock_model3

        mock_response = AsyncMock()
        mock_response.__aiter__ = lambda self: mock_list()

        mock_openai_client.models.list.return_value = mock_response

        models = await openai_adapter.list_models()

        # Should only include gpt-4 and gpt-3.5 models
        assert len(models) == 2
        assert any(m["id"] == "gpt-4o" for m in models)
        assert any(m["id"] == "gpt-3.5-turbo" for m in models)
        assert all(m["provider"] == "OpenAI" for m in models)
        assert all("display_name" in m for m in models)

    @pytest.mark.asyncio
    async def test_list_models_error(self, openai_adapter, mock_openai_client):
        """Test model listing handles errors."""
        mock_openai_client.models.list.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await openai_adapter.list_models()


class TestOpenAIAdapterErrorHandling:
    """Tests for error classification."""

    def test_is_retriable_error_429(self, openai_adapter):
        """Test 429 rate limit is retriable."""
        error = Exception("Rate limit")
        error.status_code = 429

        assert openai_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_500(self, openai_adapter):
        """Test 500 server error is retriable."""
        error = Exception("Server error")
        error.status_code = 500

        assert openai_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_503(self, openai_adapter):
        """Test 503 service unavailable is retriable."""
        error = Exception("Service unavailable")
        error.status_code = 503

        assert openai_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_rate_limit_in_message(self, openai_adapter):
        """Test rate_limit in error message is retriable."""
        error = Exception("Error: rate_limit exceeded")

        assert openai_adapter.is_retriable_error(error) is True

    def test_is_retriable_error_400(self, openai_adapter):
        """Test 400 bad request is NOT retriable."""
        error = Exception("Bad request")
        error.status_code = 400

        assert openai_adapter.is_retriable_error(error) is False

    def test_is_retriable_error_401(self, openai_adapter):
        """Test 401 unauthorized is NOT retriable."""
        error = Exception("Unauthorized")
        error.status_code = 401

        assert openai_adapter.is_retriable_error(error) is False


class TestOpenAIAdapterMessageTransform:
    """Tests for message transformation."""

    def test_transform_messages_with_system_prompt(self, openai_adapter):
        """Test messages transformed with system prompt prepended."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        system_prompt = "You are helpful"

        transformed = openai_adapter.transform_messages(messages, system_prompt)

        # System should be first message
        assert len(transformed) == 2
        assert transformed[0]["role"] == "system"
        assert transformed[0]["content"] == "You are helpful"
        assert transformed[1]["role"] == "user"

    def test_transform_messages_without_system_prompt(self, openai_adapter):
        """Test messages transformed without system prompt."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]

        transformed = openai_adapter.transform_messages(messages, None)

        # Should return unchanged
        assert len(transformed) == 1
        assert transformed[0]["role"] == "user"

    def test_transform_messages_preserves_order(self, openai_adapter):
        """Test message order is preserved."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"}
        ]

        transformed = openai_adapter.transform_messages(messages, None)

        assert len(transformed) == 3
        assert [m["content"] for m in transformed] == ["First", "Second", "Third"]
