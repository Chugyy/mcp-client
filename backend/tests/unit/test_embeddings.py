"""Unit tests for RAG embeddings service with AsyncOpenAI."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from openai import RateLimitError, APITimeoutError, APIConnectionError

# Import the functions to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.core.services.resources.rag.embeddings import generate_embedding, embed_texts


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for embeddings."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1] * 3072  # 3072-dimensional vector
    mock_response.usage.prompt_tokens = 10
    return mock_response


@pytest.fixture
def mock_openai_response_short():
    """Mock OpenAI API response with short embedding (tests padding)."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1] * 1536  # Short vector
    mock_response.usage.prompt_tokens = 10
    return mock_response


@pytest.mark.asyncio
class TestGenerateEmbedding:
    """Test suite for generate_embedding function."""

    async def test_generate_embedding_success(self, mock_openai_response):
        """Test successful embedding generation."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            result = await generate_embedding("test text")

            assert isinstance(result, list)
            assert len(result) == 3072
            assert all(isinstance(x, float) for x in result)
            mock_client.embeddings.create.assert_called_once()

    async def test_generate_embedding_with_padding(self, mock_openai_response_short):
        """Test embedding generation with automatic padding to 3072 dimensions."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response_short)

            result = await generate_embedding("test text")

            assert len(result) == 3072
            # Check that padding was applied (zeros at the end)
            assert result[1536:] == [0.0] * 1536

    async def test_generate_embedding_timeout_configuration(self, mock_openai_response):
        """Test that timeout is configured correctly (30s)."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            await generate_embedding("test text")

            call_args = mock_client.embeddings.create.call_args
            assert call_args.kwargs['timeout'] == 30.0

    async def test_generate_embedding_uses_correct_model(self, mock_openai_response):
        """Test that correct model from settings is used."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            with patch('app.core.services.resources.rag.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "text-embedding-3-large"
                mock_settings.embedding_dim = 3072
                mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

                await generate_embedding("test text")

                call_args = mock_client.embeddings.create.call_args
                assert call_args.kwargs['model'] == "text-embedding-3-large"

    async def test_generate_embedding_rate_limit_error(self):
        """Test retry behavior on rate limit error."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(
                side_effect=RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)
            )

            with pytest.raises(RateLimitError):
                await generate_embedding("test text")

            # Should retry 3 times (initial + 2 retries = 3 total attempts)
            assert mock_client.embeddings.create.call_count == 3

    async def test_generate_embedding_timeout_error(self):
        """Test retry behavior on timeout error."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(
                side_effect=APITimeoutError("Request timed out")
            )

            with pytest.raises(APITimeoutError):
                await generate_embedding("test text")

            # Should retry 3 times
            assert mock_client.embeddings.create.call_count == 3

    async def test_generate_embedding_connection_error(self):
        """Test retry behavior on connection error."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            # Create APIConnectionError with request parameter
            error = APIConnectionError(request=MagicMock())
            mock_client.embeddings.create = AsyncMock(side_effect=error)

            with pytest.raises(APIConnectionError):
                await generate_embedding("test text")

            # Should retry 3 times
            assert mock_client.embeddings.create.call_count == 3

    async def test_generate_embedding_non_retriable_error(self):
        """Test that non-retriable errors are not retried."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(
                side_effect=ValueError("Invalid input")
            )

            with pytest.raises(ValueError):
                await generate_embedding("test text")

            # Should NOT retry on non-retriable errors
            assert mock_client.embeddings.create.call_count == 1


@pytest.mark.asyncio
class TestEmbedTexts:
    """Test suite for embed_texts batch function."""

    async def test_embed_texts_empty_list(self):
        """Test that empty input returns empty output."""
        result = await embed_texts([])
        assert result == []

    async def test_embed_texts_single_text(self, mock_openai_response):
        """Test batch embedding with single text."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            result = await embed_texts(["test text"])

            assert len(result) == 1
            assert len(result[0]) == 3072

    async def test_embed_texts_multiple_texts(self, mock_openai_response):
        """Test batch embedding with multiple texts."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            texts = ["text 1", "text 2", "text 3"]
            result = await embed_texts(texts)

            assert len(result) == 3
            assert all(len(emb) == 3072 for emb in result)
            # Should be called 3 times (once per text)
            assert mock_client.embeddings.create.call_count == 3

    async def test_embed_texts_batch_processing(self, mock_openai_response):
        """Test that large batches are processed correctly."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            # Create 250 texts to test batching (should process in 3 batches of 100, 100, 50)
            texts = [f"text {i}" for i in range(250)]
            result = await embed_texts(texts, batch_size=100)

            assert len(result) == 250
            assert all(len(emb) == 3072 for emb in result)
            # Should be called 250 times (once per text)
            assert mock_client.embeddings.create.call_count == 250

    async def test_embed_texts_concurrent_execution(self, mock_openai_response):
        """Test that embeddings are generated concurrently within batches."""
        call_times = []

        async def mock_create_with_delay(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)  # Simulate API delay
            return mock_openai_response

        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            mock_client.embeddings.create = mock_create_with_delay

            texts = [f"text {i}" for i in range(5)]
            start_time = asyncio.get_event_loop().time()
            result = await embed_texts(texts, batch_size=100)
            end_time = asyncio.get_event_loop().time()

            # If concurrent, should take ~0.1s (not 0.5s sequential)
            elapsed = end_time - start_time
            assert elapsed < 0.3  # Allow some overhead
            assert len(result) == 5

    async def test_embed_texts_preserves_order(self, mock_openai_response):
        """Test that output order matches input order."""
        with patch('app.core.services.resources.rag.embeddings.client') as mock_client:
            # Return different embeddings for each call
            call_count = [0]

            async def mock_create(*args, **kwargs):
                response = MagicMock()
                response.data = [MagicMock()]
                # Create unique embedding based on call count
                response.data[0].embedding = [float(call_count[0])] * 3072
                response.usage.prompt_tokens = 10
                call_count[0] += 1
                return response

            mock_client.embeddings.create = mock_create

            texts = [f"text {i}" for i in range(5)]
            result = await embed_texts(texts)

            # Check that embeddings are in the same order as inputs
            for i, embedding in enumerate(result):
                assert embedding[0] == float(i)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
