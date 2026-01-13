"""Integration tests for LLM tool calls via MCP."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.services.llm.gateway import LLMGateway
from app.core.services.llm.types import ToolDefinition, ToolCall, ToolResult
from app.core.services.llm.adapters.anthropic import AnthropicAdapter
from app.core.services.llm.adapters.openai import OpenAIAdapter


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    with patch('app.core.services.llm.gateway.settings') as mock_settings:
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        yield mock_settings


@pytest.fixture
def sample_tools():
    """Sample tool definitions for testing."""
    return [
        ToolDefinition(
            name="get_weather",
            description="Get current weather for a location",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            },
            server_id="weather-server"
        ),
        ToolDefinition(
            name="calculate",
            description="Perform calculation",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            },
            server_id="calc-server"
        )
    ]


class TestToolCallDetection:
    """Tests for tool call detection in LLM responses."""

    @pytest.mark.asyncio
    async def test_anthropic_tool_call_detection(self, mock_settings, sample_tools):
        """Test Anthropic adapter detects tool calls correctly."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Mock tool_use event stream
            async def mock_event_stream():
                # Start tool_use
                event1 = MagicMock()
                event1.type = "content_block_start"
                event1.content_block = MagicMock()
                event1.content_block.type = "tool_use"
                event1.content_block.id = "call_weather_123"
                event1.content_block.name = "get_weather"
                yield event1

                # Arguments JSON
                event2 = MagicMock()
                event2.type = "content_block_delta"
                event2.delta = MagicMock()
                event2.delta.type = "input_json_delta"
                event2.delta.partial_json = '{"location": "Paris", "units": "celsius"}'
                yield event2

                # End block
                event3 = MagicMock()
                event3.type = "content_block_stop"
                yield event3

            mock_stream = AsyncMock()
            mock_stream.__aiter__.return_value = mock_event_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "What's the weather in Paris?"}],
                tools=sample_tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            # Should detect one tool call
            assert len(chunks) == 1
            assert isinstance(chunks[0], ToolCall)
            assert chunks[0].id == "call_weather_123"
            assert chunks[0].name == "get_weather"
            assert chunks[0].arguments == {"location": "Paris", "units": "celsius"}

    @pytest.mark.asyncio
    async def test_openai_tool_call_detection(self, mock_settings, sample_tools):
        """Test OpenAI adapter detects tool calls correctly."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            # Mock tool_calls stream
            async def mock_stream():
                # Start tool call
                chunk1 = MagicMock()
                chunk1.choices = [MagicMock()]
                chunk1.choices[0].delta = MagicMock()
                chunk1.choices[0].delta.content = None

                tc = MagicMock()
                tc.index = 0
                tc.id = "call_calc_456"
                tc.function = MagicMock()
                tc.function.name = "calculate"
                tc.function.arguments = '{"expression": "2 + 2"}'

                chunk1.choices[0].delta.tool_calls = [tc]
                chunk1.choices[0].finish_reason = None
                yield chunk1

                # Finish
                chunk2 = MagicMock()
                chunk2.choices = [MagicMock()]
                chunk2.choices[0].delta = MagicMock()
                chunk2.choices[0].delta.content = None
                chunk2.choices[0].delta.tool_calls = None
                chunk2.choices[0].finish_reason = "tool_calls"
                yield chunk2

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Calculate 2 + 2"}],
                tools=sample_tools,
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            # Should detect one tool call
            assert len(chunks) == 1
            assert isinstance(chunks[0], ToolCall)
            assert chunks[0].id == "call_calc_456"
            assert chunks[0].name == "calculate"
            assert chunks[0].arguments == {"expression": "2 + 2"}


class TestToolParameterParsing:
    """Tests for tool parameter parsing."""

    @pytest.mark.asyncio
    async def test_anthropic_parse_simple_parameters(self, mock_settings, sample_tools):
        """Test parsing simple string parameters."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_event_stream():
                # Tool use with simple params
                event1 = MagicMock()
                event1.type = "content_block_start"
                event1.content_block = MagicMock()
                event1.content_block.type = "tool_use"
                event1.content_block.id = "call_1"
                event1.content_block.name = "get_weather"
                yield event1

                event2 = MagicMock()
                event2.type = "content_block_delta"
                event2.delta = MagicMock()
                event2.delta.type = "input_json_delta"
                event2.delta.partial_json = '{"location": "London"}'
                yield event2

                event3 = MagicMock()
                event3.type = "content_block_stop"
                yield event3

            mock_stream = AsyncMock()
            mock_stream.__aiter__.return_value = mock_event_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Weather?"}],
                tools=sample_tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            assert chunks[0].arguments["location"] == "London"

    @pytest.mark.asyncio
    async def test_anthropic_parse_complex_parameters(self, mock_settings):
        """Test parsing complex nested parameters."""
        tools = [
            ToolDefinition(
                name="complex_tool",
                description="Tool with complex params",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "items": {"type": "array"}
                            }
                        }
                    }
                },
                server_id="test"
            )
        ]

        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_event_stream():
                event1 = MagicMock()
                event1.type = "content_block_start"
                event1.content_block = MagicMock()
                event1.content_block.type = "tool_use"
                event1.content_block.id = "call_2"
                event1.content_block.name = "complex_tool"
                yield event1

                event2 = MagicMock()
                event2.type = "content_block_delta"
                event2.delta = MagicMock()
                event2.delta.type = "input_json_delta"
                event2.delta.partial_json = '{"data": {"items": [1, 2, 3]}}'
                yield event2

                event3 = MagicMock()
                event3.type = "content_block_stop"
                yield event3

            mock_stream = AsyncMock()
            mock_stream.__aiter__.return_value = mock_event_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Complex"}],
                tools=tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            assert chunks[0].arguments["data"]["items"] == [1, 2, 3]


class TestToolResultHandling:
    """Tests for tool result handling."""

    @pytest.mark.asyncio
    async def test_tool_result_format(self):
        """Test ToolResult format."""
        result = ToolResult(
            tool_call_id="call_123",
            content='{"temperature": 22}',
            is_error=False
        )

        assert result.tool_call_id == "call_123"
        assert result.content == '{"temperature": 22}'
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_tool_error_result(self):
        """Test ToolResult for errors."""
        result = ToolResult(
            tool_call_id="call_456",
            content="Tool execution failed: timeout",
            is_error=True
        )

        assert result.is_error is True
        assert "timeout" in result.content


class TestMultiTurnToolConversations:
    """Tests for multi-turn conversations with tools."""

    @pytest.mark.asyncio
    async def test_anthropic_multi_turn_tool_conversation(self, mock_settings, sample_tools):
        """Test multi-turn tool conversation with Anthropic."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Turn 1: User asks for weather
            # Turn 2: LLM requests tool
            # Turn 3: Tool result provided
            # Turn 4: LLM responds with final answer

            # Mock first stream (LLM requests tool)
            async def mock_stream_1():
                event = MagicMock()
                event.type = "content_block_start"
                event.content_block = MagicMock()
                event.content_block.type = "tool_use"
                event.content_block.id = "call_1"
                event.content_block.name = "get_weather"
                yield event

                event2 = MagicMock()
                event2.type = "content_block_delta"
                event2.delta = MagicMock()
                event2.delta.type = "input_json_delta"
                event2.delta.partial_json = '{"location": "Paris"}'
                yield event2

                event3 = MagicMock()
                event3.type = "content_block_stop"
                yield event3

            # Mock second stream (LLM responds after tool result)
            async def mock_stream_2():
                event = MagicMock()
                event.type = "content_block_delta"
                event.delta = MagicMock()
                event.delta.type = "text_delta"
                event.delta.text = "The weather in Paris is 22°C."
                yield event

            mock_stream_obj_1 = AsyncMock()
            mock_stream_obj_1.__aiter__.return_value = mock_stream_1()
            mock_stream_obj_1.__aenter__.return_value = mock_stream_obj_1
            mock_stream_obj_1.__aexit__.return_value = None

            mock_stream_obj_2 = AsyncMock()
            mock_stream_obj_2.__aiter__.return_value = mock_stream_2()
            mock_stream_obj_2.__aenter__.return_value = mock_stream_obj_2
            mock_stream_obj_2.__aexit__.return_value = None

            # Return different streams on successive calls
            mock_client.messages.stream.side_effect = [mock_stream_obj_1, mock_stream_obj_2]
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            # First turn: Get tool call
            chunks_1 = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Weather in Paris?"}],
                tools=sample_tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks_1.append(chunk)

            assert isinstance(chunks_1[0], ToolCall)
            assert chunks_1[0].name == "get_weather"

            # Second turn: Provide tool result
            messages_with_result = [
                {"role": "user", "content": "Weather in Paris?"},
                {"role": "assistant", "content": [{"type": "tool_use", "id": "call_1", "name": "get_weather"}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": '{"temp": 22}'}]}
            ]

            chunks_2 = []
            async for chunk in adapter.stream_with_tools(
                messages=messages_with_result,
                tools=sample_tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks_2.append(chunk)

            # Should get text response
            assert isinstance(chunks_2[0], str)
            assert "22" in chunks_2[0]


class TestMultipleToolCalls:
    """Tests for multiple tool calls in single response."""

    @pytest.mark.asyncio
    async def test_openai_multiple_tool_calls(self, mock_settings, sample_tools):
        """Test OpenAI handles multiple tool calls."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

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
                tc1.function.name = "get_weather"
                tc1.function.arguments = '{"location": "Paris"}'

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
                tc2.function.name = "calculate"
                tc2.function.arguments = '{"expression": "2*3"}'

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

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Weather and calc"}],
                tools=sample_tools,
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            # Should have 2 tool calls
            assert len(chunks) == 2
            assert all(isinstance(c, ToolCall) for c in chunks)
            assert chunks[0].name == "get_weather"
            assert chunks[1].name == "calculate"


class TestToolCallEdgeCases:
    """Tests for tool call edge cases."""

    @pytest.mark.asyncio
    async def test_anthropic_tool_call_empty_parameters(self, mock_settings):
        """Test tool call with no parameters."""
        tools = [
            ToolDefinition(
                name="no_params_tool",
                description="Tool with no params",
                input_schema={"type": "object", "properties": {}},
                server_id="test"
            )
        ]

        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_event_stream():
                event1 = MagicMock()
                event1.type = "content_block_start"
                event1.content_block = MagicMock()
                event1.content_block.type = "tool_use"
                event1.content_block.id = "call_empty"
                event1.content_block.name = "no_params_tool"
                yield event1

                # No input_json_delta events (empty params)

                event2 = MagicMock()
                event2.type = "content_block_stop"
                yield event2

            mock_stream = AsyncMock()
            mock_stream.__aiter__.return_value = mock_event_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream_with_tools(
                messages=[{"role": "user", "content": "Call tool"}],
                tools=tools,
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            # Should create ToolCall with empty arguments
            assert chunks[0].arguments == {}
