"""Pytest configuration and fixtures for RAG pipeline tests."""

import pytest
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List


@pytest.fixture
def mock_embedding_client():
    """Mock embedding client for deterministic tests without API calls."""

    class MockEmbeddingClient:
        """Mock OpenAI embedding client with deterministic outputs."""

        def __init__(self):
            self.call_count = 0
            self.cache = {}

        async def generate_embedding(self, text: str) -> List[float]:
            """Generate deterministic mock embedding based on text hash.

            Args:
                text: Input text to embed

            Returns:
                List of 3072 floats (OpenAI text-embedding-3-large dimension)
            """
            # Use cached embedding if available
            if text in self.cache:
                return self.cache[text]

            # Generate deterministic embedding from text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            base_value = int(text_hash[:8], 16) / (16**8)  # 0-1 range

            # Create 3072-dimensional vector with slight variations
            embedding = []
            for i in range(3072):
                offset = (int(text_hash[i % 32], 16) / 16.0) * 0.1  # Small variation
                embedding.append(base_value + offset - 0.05)  # Center around base_value

            self.cache[text] = embedding
            self.call_count += 1
            return embedding

        async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
            """Generate embeddings for multiple texts.

            Args:
                texts: List of input texts

            Returns:
                List of embedding vectors
            """
            return [await self.generate_embedding(text) for text in texts]

    return MockEmbeddingClient()


@pytest.fixture
def sample_document():
    """Sample document for testing RAG ingestion."""
    return {
        "content": (
            "This is a test document about AI and machine learning. "
            "Artificial intelligence is transforming how we build software. "
            "Machine learning models can process vast amounts of data. "
            "Natural language processing enables human-computer interaction. "
            "Deep learning uses neural networks for complex pattern recognition. "
        ) * 20,  # Repeat to create substantial content for chunking
        "title": "AI and Machine Learning Guide",
        "metadata": {
            "author": "Test Author",
            "date": "2026-01-06",
            "category": "technology"
        }
    }


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing embedding generation."""
    return [
        "Artificial intelligence is the simulation of human intelligence.",
        "Machine learning is a subset of AI focused on learning from data.",
        "Natural language processing deals with text and speech understanding.",
        "Computer vision enables machines to interpret visual information.",
        "Reinforcement learning trains agents through reward-based feedback."
    ]


@pytest.fixture
async def mock_openai_client(mock_embedding_client):
    """Mock AsyncOpenAI client for embeddings tests.

    Returns a patched AsyncOpenAI that uses our deterministic mock.
    """
    # Create mock response structure matching OpenAI API
    def create_mock_response(embeddings_data):
        mock_response = MagicMock()
        mock_response.data = []

        for embedding in embeddings_data:
            mock_data_item = MagicMock()
            mock_data_item.embedding = embedding
            mock_response.data.append(mock_data_item)

        # Add usage info
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = sum(len(emb) for emb in embeddings_data)

        return mock_response

    async def mock_create(**kwargs):
        """Mock embeddings.create() call."""
        input_text = kwargs.get('input', '')

        if isinstance(input_text, str):
            embedding = await mock_embedding_client.generate_embedding(input_text)
            return create_mock_response([embedding])
        elif isinstance(input_text, list):
            embeddings = await mock_embedding_client.generate_embeddings(input_text)
            return create_mock_response(embeddings)

    # Create mock client
    mock_client = AsyncMock()
    mock_client.embeddings = AsyncMock()
    mock_client.embeddings.create = AsyncMock(side_effect=mock_create)

    # Patch AsyncOpenAI
    with patch('app.core.services.resources.rag.embeddings.client', mock_client):
        yield mock_client


@pytest.fixture
async def mock_get_connection():
    """Mock database connection for RAG tests.

    Provides a mock connection with basic execute/fetch methods.
    """
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
            yield mock_conn


@pytest.fixture
def mock_upload_data():
    """Mock upload data for ingestion tests."""
    return {
        'id': 'test-upload-id',
        'file_path': '/tmp/test_document.txt',
        'mime_type': 'text/plain',
        'resource_id': 'test-resource-id',
        'status': 'uploaded'
    }


@pytest.fixture
def mock_resource_data():
    """Mock resource data for tests."""
    return {
        'id': 'test-resource-id',
        'name': 'Test Resource',
        'description': 'A test resource for RAG pipeline',
        'status': 'pending',
        'chunk_count': 0
    }


@pytest.fixture
def mock_embedding_rows():
    """Mock database rows for vector search results."""
    return [
        {
            'id': 'emb-1',
            'text': 'Artificial intelligence is transforming software development.',
            'resource_id': 'res-1',
            'upload_id': 'upload-1',
            'chunk_index': 0,
            'distance': 0.15,
            'resource_name': 'AI Guide'
        },
        {
            'id': 'emb-2',
            'text': 'Machine learning enables systems to learn from data.',
            'resource_id': 'res-1',
            'upload_id': 'upload-1',
            'chunk_index': 1,
            'distance': 0.22,
            'resource_name': 'AI Guide'
        },
        {
            'id': 'emb-3',
            'text': 'Neural networks are the foundation of deep learning.',
            'resource_id': 'res-2',
            'upload_id': 'upload-2',
            'chunk_index': 0,
            'distance': 0.35,
            'resource_name': 'Deep Learning Basics'
        }
    ]
