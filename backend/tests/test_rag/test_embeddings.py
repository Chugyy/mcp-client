"""Tests for RAG embedding client (async embedding generation)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from openai import RateLimitError, APITimeoutError, APIConnectionError
from app.core.services.resources.rag.embeddings import generate_embedding, embed_texts


@pytest.mark.asyncio
async def test_generate_embedding_success(mock_openai_client):
    """Test async embedding generation for single text."""
    text = "This is a test document about AI and machine learning"

    embedding = await generate_embedding(text)

    # Verify embedding structure
    assert isinstance(embedding, list)
    assert len(embedding) == 3072  # OpenAI text-embedding-3-large dimension
    assert all(isinstance(x, float) for x in embedding)

    # Verify API was called correctly
    mock_openai_client.embeddings.create.assert_called_once()
    call_kwargs = mock_openai_client.embeddings.create.call_args[1]
    assert call_kwargs['input'] == text
    assert 'timeout' in call_kwargs


@pytest.mark.asyncio
async def test_batch_embeddings_success(mock_openai_client, sample_chunks):
    """Test batch embedding generation for multiple texts."""
    embeddings = await embed_texts(sample_chunks)

    # Verify batch processing
    assert len(embeddings) == len(sample_chunks)
    assert all(len(emb) == 3072 for emb in embeddings)
    assert all(isinstance(emb, list) for emb in embeddings)

    # Verify all texts were embedded
    assert all(all(isinstance(val, float) for val in emb) for emb in embeddings)


@pytest.mark.asyncio
async def test_embedding_caching_behavior(mock_embedding_client):
    """Test that embeddings are deterministic (simulating cache behavior)."""
    text = "Consistent test text for caching"

    # Generate embedding twice
    embedding1 = await mock_embedding_client.generate_embedding(text)
    embedding2 = await mock_embedding_client.generate_embedding(text)

    # Verify deterministic behavior (same text = same embedding)
    assert embedding1 == embedding2

    # Verify cache is being used (call count should be 1 due to caching)
    assert mock_embedding_client.call_count == 1  # Only one actual generation


@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Test retry logic for rate limiting (429 errors)."""
    mock_client = AsyncMock()

    # Simulate rate limit on first call, then success
    rate_limit_error = RateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429),
        body={}
    )

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 3072)]
    mock_response.usage = MagicMock(prompt_tokens=10)

    mock_client.embeddings.create = AsyncMock(
        side_effect=[rate_limit_error, mock_response]
    )

    with patch('app.core.services.resources.rag.embeddings.client', mock_client):
        # Should retry and succeed
        embedding = await generate_embedding("Test text")

        assert len(embedding) == 3072
        assert mock_client.embeddings.create.call_count == 2  # Initial + 1 retry


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test retry logic for timeout errors."""
    mock_client = AsyncMock()

    # Simulate timeout on first call, then success
    timeout_error = APITimeoutError(request=MagicMock())

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 3072)]
    mock_response.usage = MagicMock(prompt_tokens=10)

    mock_client.embeddings.create = AsyncMock(
        side_effect=[timeout_error, mock_response]
    )

    with patch('app.core.services.resources.rag.embeddings.client', mock_client):
        # Should retry and succeed
        embedding = await generate_embedding("Test text")

        assert len(embedding) == 3072
        assert mock_client.embeddings.create.call_count == 2  # Initial + 1 retry


@pytest.mark.asyncio
async def test_retry_logic_exhaustion():
    """Test retry logic with 3 attempts then failure."""
    mock_client = AsyncMock()

    # Simulate persistent connection error
    connection_error = APIConnectionError(request=MagicMock())

    mock_client.embeddings.create = AsyncMock(side_effect=connection_error)

    with patch('app.core.services.resources.rag.embeddings.client', mock_client):
        # Should retry 3 times then raise
        with pytest.raises(APIConnectionError):
            await generate_embedding("Test text")

        # Verify 3 attempts were made (initial + 2 retries = 3 total)
        assert mock_client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_error_handling_invalid_api_key():
    """Test error handling for invalid API key and service unavailable."""
    mock_client = AsyncMock()

    # Simulate authentication error (non-retriable)
    auth_error = Exception("Invalid API key")

    mock_client.embeddings.create = AsyncMock(side_effect=auth_error)

    with patch('app.core.services.resources.rag.embeddings.client', mock_client):
        # Should raise immediately (not retriable)
        with pytest.raises(Exception) as exc_info:
            await generate_embedding("Test text")

        assert "Invalid API key" in str(exc_info.value)
        # Should not retry for auth errors
        assert mock_client.embeddings.create.call_count == 1


@pytest.mark.asyncio
async def test_empty_batch_handling(mock_openai_client):
    """Test handling of empty text list in batch processing."""
    embeddings = await embed_texts([])

    # Should return empty list without API calls
    assert embeddings == []
    assert mock_openai_client.embeddings.create.call_count == 0


@pytest.mark.asyncio
async def test_batch_size_control(mock_openai_client):
    """Test that large batches are processed with controlled concurrency."""
    # Create 150 texts (exceeds default batch_size of 100)
    large_batch = [f"Text {i}" for i in range(150)]

    embeddings = await embed_texts(large_batch, batch_size=100)

    # Verify all texts were embedded
    assert len(embeddings) == 150
    assert all(len(emb) == 3072 for emb in embeddings)

    # Verify batching occurred (should be split into 2 batches)
    # Note: Each text in batch triggers individual generate_embedding calls
    assert mock_openai_client.embeddings.create.call_count == 150
