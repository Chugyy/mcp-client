"""Integration tests for LLM SSE streaming."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.core.services.llm.gateway import LLMGateway
from app.core.services.llm.adapters.anthropic import AnthropicAdapter
from app.core.services.llm.adapters.openai import OpenAIAdapter


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    with patch('app.core.services.llm.gateway.settings') as mock_settings:
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        yield mock_settings


class TestStreamingChunkDelivery:
    """Tests for chunk-by-chunk delivery of streaming responses."""

    @pytest.mark.asyncio
    async def test_anthropic_stream_chunk_delivery(self, mock_settings):
        """Test Anthropic streaming delivers chunks progressively."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Mock streaming response
            async def mock_text_stream():
                yield "First"
                await asyncio.sleep(0.01)  # Simulate network delay
                yield " "
                await asyncio.sleep(0.01)
                yield "chunk"
                await asyncio.sleep(0.01)
                yield "."

            mock_stream = AsyncMock()
            mock_stream.text_stream = mock_text_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            # Collect chunks with timestamps
            chunks = []
            start_time = asyncio.get_event_loop().time()

            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append({
                    "text": chunk,
                    "time": asyncio.get_event_loop().time() - start_time
                })

            # Verify chunks arrive progressively
            assert len(chunks) == 4
            assert chunks[0]["text"] == "First"
            assert chunks[1]["text"] == " "
            assert chunks[2]["text"] == "chunk"
            assert chunks[3]["text"] == "."

            # Verify chunks arrive with delays (progressive streaming)
            assert chunks[1]["time"] > chunks[0]["time"]
            assert chunks[2]["time"] > chunks[1]["time"]

    @pytest.mark.asyncio
    async def test_openai_stream_chunk_delivery(self, mock_settings):
        """Test OpenAI streaming delivers chunks progressively."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            # Mock streaming response
            async def mock_stream():
                chunk1 = MagicMock()
                chunk1.choices = [MagicMock()]
                chunk1.choices[0].delta = MagicMock()
                chunk1.choices[0].delta.content = "Hello"
                yield chunk1
                await asyncio.sleep(0.01)

                chunk2 = MagicMock()
                chunk2.choices = [MagicMock()]
                chunk2.choices[0].delta = MagicMock()
                chunk2.choices[0].delta.content = " "
                yield chunk2
                await asyncio.sleep(0.01)

                chunk3 = MagicMock()
                chunk3.choices = [MagicMock()]
                chunk3.choices[0].delta = MagicMock()
                chunk3.choices[0].delta.content = "world"
                yield chunk3

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            assert chunks == ["Hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_gateway_stream_chunk_delivery(self, mock_settings):
        """Test gateway preserves chunk-by-chunk delivery."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_stream():
                for word in ["Chunk", "1", " ", "Chunk", "2"]:
                    chunk = MagicMock()
                    chunk.choices = [MagicMock()]
                    chunk.choices[0].delta = MagicMock()
                    chunk.choices[0].delta.content = word
                    yield chunk
                    await asyncio.sleep(0.001)

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="openai"), \
                 patch('app.core.services.llm.gateway.transform_params', return_value={"model": "gpt-4o-mini"}):

                gateway = LLMGateway()

                chunks = []
                async for chunk in gateway.stream(
                    messages=[{"role": "user", "content": "Hello"}],
                    model="gpt-4o-mini"
                ):
                    chunks.append(chunk)

                assert chunks == ["Chunk", "1", " ", "Chunk", "2"]


class TestStreamTermination:
    """Tests for proper stream termination."""

    @pytest.mark.asyncio
    async def test_anthropic_stream_termination(self, mock_settings):
        """Test Anthropic stream terminates cleanly."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_text_stream():
                yield "Text"
                # Stream ends naturally

            mock_stream = AsyncMock()
            mock_stream.text_stream = mock_text_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            # Stream should end after last chunk
            assert len(chunks) == 1

            # Verify context manager cleanup was called
            mock_stream.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_stream_termination(self, mock_settings):
        """Test OpenAI stream terminates cleanly."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = "Done"
                yield chunk
                # Stream ends

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            assert chunks == ["Done"]


class TestStreamErrorHandling:
    """Tests for error handling during streaming."""

    @pytest.mark.asyncio
    async def test_anthropic_stream_error_mid_stream(self, mock_settings):
        """Test Anthropic handles errors mid-stream."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_text_stream():
                yield "Start"
                raise Exception("Stream error")

            mock_stream = AsyncMock()
            mock_stream.text_stream = mock_text_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            with pytest.raises(Exception, match="Stream error"):
                async for chunk in adapter.stream(
                    messages=[{"role": "user", "content": "Hello"}],
                    model="claude-sonnet-4",
                    max_tokens=1024
                ):
                    chunks.append(chunk)

            # Should have received chunk before error
            assert len(chunks) == 1
            assert chunks[0] == "Start"

    @pytest.mark.asyncio
    async def test_openai_stream_error_mid_stream(self, mock_settings):
        """Test OpenAI handles errors mid-stream."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = "Begin"
                yield chunk

                raise Exception("Connection lost")

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            with pytest.raises(Exception, match="Connection lost"):
                async for chunk in adapter.stream(
                    messages=[{"role": "user", "content": "Hello"}],
                    model="gpt-4o-mini"
                ):
                    chunks.append(chunk)

            assert chunks == ["Begin"]


class TestStreamNoDataLoss:
    """Tests for data integrity during streaming."""

    @pytest.mark.asyncio
    async def test_anthropic_no_data_loss(self, mock_settings):
        """Test all chunks are delivered without loss."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Generate 100 chunks
            async def mock_text_stream():
                for i in range(100):
                    yield str(i) + ","

            mock_stream = AsyncMock()
            mock_stream.text_stream = mock_text_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Count"}],
                model="claude-sonnet-4",
                max_tokens=1024
            ):
                chunks.append(chunk)

            # All 100 chunks should be present
            assert len(chunks) == 100
            reconstructed = "".join(chunks)
            expected = ",".join(str(i) for i in range(100)) + ","
            assert reconstructed == expected

    @pytest.mark.asyncio
    async def test_openai_no_data_loss(self, mock_settings):
        """Test all chunks are delivered without loss."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            async def mock_stream():
                for i in range(50):
                    chunk = MagicMock()
                    chunk.choices = [MagicMock()]
                    chunk.choices[0].delta = MagicMock()
                    chunk.choices[0].delta.content = f"{i};"
                    yield chunk

            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Count"}],
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            # All 50 chunks should be present
            assert len(chunks) == 50
            reconstructed = "".join(chunks)
            expected = ";".join(f"{i}" for i in range(50)) + ";"
            assert reconstructed == expected


class TestStreamConcurrency:
    """Tests for concurrent streaming requests."""

    @pytest.mark.asyncio
    async def test_concurrent_streams_no_interference(self, mock_settings):
        """Test concurrent streams don't interfere with each other."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            call_count = 0

            async def mock_stream():
                nonlocal call_count
                call_count += 1
                stream_id = call_count

                for i in range(5):
                    chunk = MagicMock()
                    chunk.choices = [MagicMock()]
                    chunk.choices[0].delta = MagicMock()
                    chunk.choices[0].delta.content = f"S{stream_id}-{i}"
                    yield chunk
                    await asyncio.sleep(0.001)

            mock_client.chat.completions.create = AsyncMock(side_effect=lambda **kwargs: mock_stream())
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            # Start 3 concurrent streams
            async def collect_stream(stream_num):
                chunks = []
                async for chunk in adapter.stream(
                    messages=[{"role": "user", "content": f"Stream {stream_num}"}],
                    model="gpt-4o-mini"
                ):
                    chunks.append(chunk)
                return chunks

            results = await asyncio.gather(
                collect_stream(1),
                collect_stream(2),
                collect_stream(3)
            )

            # Each stream should have 5 chunks
            assert all(len(chunks) == 5 for chunks in results)

            # Chunks should belong to their respective streams
            for i, chunks in enumerate(results, 1):
                # Each chunk should start with correct stream ID
                assert all(chunk.startswith(f"S{i}-") for chunk in chunks)


class TestStreamLargeResponses:
    """Tests for handling large streaming responses."""

    @pytest.mark.asyncio
    async def test_anthropic_large_response(self, mock_settings):
        """Test Anthropic handles large streaming responses."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Generate large response (simulate 1000 tokens)
            async def mock_text_stream():
                for i in range(1000):
                    yield f"token{i} "

            mock_stream = AsyncMock()
            mock_stream.text_stream = mock_text_stream()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.__aexit__.return_value = None

            mock_client.messages.stream.return_value = mock_stream
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            chunks = []
            async for chunk in adapter.stream(
                messages=[{"role": "user", "content": "Generate large text"}],
                model="claude-sonnet-4",
                max_tokens=2000
            ):
                chunks.append(chunk)

            # Should handle all 1000 chunks
            assert len(chunks) == 1000
            # Verify content
            full_text = "".join(chunks)
            assert "token0 " in full_text
            assert "token999 " in full_text
