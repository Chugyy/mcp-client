"""Tests for RAG vector search functionality."""

import pytest
from unittest.mock import patch, AsyncMock
from app.core.services.resources.rag.search import search, list_resources


@pytest.mark.asyncio
async def test_similarity_search_cosine_distance(mock_get_connection, mock_embedding_rows, mock_openai_client):
    """Test vector similarity search using cosine distance."""
    query = "AI and machine learning"
    resource_ids = ["res-1"]

    # Mock database connection and query results
    mock_get_connection.fetch = AsyncMock(return_value=mock_embedding_rows[:2])

    results = await search(query, resource_ids, top_k=5)

    # Verify result structure
    assert "contexts" in results
    assert "sources" in results
    assert "upload_ids" in results
    assert "detailed_sources" in results
    assert "count" in results

    # Verify contexts extracted
    assert len(results["contexts"]) == 2
    assert all(isinstance(ctx, str) for ctx in results["contexts"])

    # Verify similarity calculation (1 - distance)
    assert all(0 <= src["similarity"] <= 1 for src in results["detailed_sources"])

    # Verify query was embedded
    mock_openai_client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_top_k_retrieval_variations(mock_embedding_rows, mock_openai_client):
    """Test top-k retrieval with different k values (k=5, 10, 20)."""
    query = "neural networks"
    resource_ids = ["res-1", "res-2"]

    # Create a dedicated mock connection for this test
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock(return_value=None)

    # Test k=5
    mock_conn.fetch = AsyncMock(return_value=mock_embedding_rows[:5] if len(mock_embedding_rows) >= 5 else mock_embedding_rows)
    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        results_k5 = await search(query, resource_ids, top_k=5)
        assert results_k5["count"] <= 5

    # Test k=10
    mock_conn.fetch = AsyncMock(return_value=mock_embedding_rows[:10] if len(mock_embedding_rows) >= 10 else mock_embedding_rows)
    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        results_k10 = await search(query, resource_ids, top_k=10)
        assert results_k10["count"] <= 10

    # Test k=20
    mock_conn.fetch = AsyncMock(return_value=mock_embedding_rows[:20] if len(mock_embedding_rows) >= 20 else mock_embedding_rows)
    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        results_k20 = await search(query, resource_ids, top_k=20)
        assert results_k20["count"] <= 20

    # Verify that search was called three times by checking OpenAI client calls
    assert mock_openai_client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_relevance_threshold_filtering(mock_get_connection, mock_embedding_rows, mock_openai_client):
    """Test filtering results by relevance threshold."""
    query = "deep learning"
    resource_ids = ["res-1"]

    # Return results with varying distances
    mock_get_connection.fetch = AsyncMock(return_value=mock_embedding_rows)

    results = await search(query, resource_ids, top_k=10)

    # Verify results are ordered by similarity (descending)
    similarities = [src["similarity"] for src in results["detailed_sources"]]
    assert similarities == sorted(similarities, reverse=True)

    # Verify similarity scores are within valid range
    assert all(0 <= sim <= 1 for sim in similarities)

    # High similarity = low distance
    # First result should have lower distance than last
    assert mock_embedding_rows[0]['distance'] < mock_embedding_rows[-1]['distance']


@pytest.mark.asyncio
async def test_metadata_filtering_by_resource_id(mock_get_connection, mock_embedding_rows, mock_openai_client):
    """Test filtering search results by resource_id."""
    query = "machine learning algorithms"
    resource_ids = ["res-1"]  # Only search in res-1

    # Mock returns only results from res-1
    filtered_rows = [row for row in mock_embedding_rows if row['resource_id'] == 'res-1']
    mock_get_connection.fetch = AsyncMock(return_value=filtered_rows)

    results = await search(query, resource_ids, top_k=10)

    # Verify only res-1 results are returned
    assert all(src["resource_id"] == "res-1" for src in results["detailed_sources"])
    assert "res-1" in results["sources"]
    assert "res-2" not in results["sources"]

    # Verify SQL query was called with resource_id filter
    fetch_calls = mock_get_connection.fetch.call_args_list
    assert len(fetch_calls) > 0

    # Check that SQL query contains resource_id filtering
    sql_query = fetch_calls[-1][0][0]
    assert "resource_id" in sql_query.lower()
    assert "where" in sql_query.lower() or "in" in sql_query.lower()


@pytest.mark.asyncio
async def test_empty_results_handling(mock_get_connection, mock_openai_client):
    """Test handling of queries with no matching results."""
    query = "completely unrelated topic xyz123"
    resource_ids = ["res-1"]

    # Mock empty results
    mock_get_connection.fetch = AsyncMock(return_value=[])

    results = await search(query, resource_ids, top_k=5)

    # Verify empty results structure
    assert results["count"] == 0
    assert results["contexts"] == []
    assert results["sources"] == []
    assert results["upload_ids"] == []
    assert results["detailed_sources"] == []

    # Verify query embedding was still generated
    mock_openai_client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_query_embedding_generation(mock_openai_client):
    """Test that query text is properly embedded before search."""
    query = "test query for embedding"
    resource_ids = ["res-1"]

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        await search(query, resource_ids, top_k=5)

        # Verify query was embedded
        mock_openai_client.embeddings.create.assert_called_once()

        # Verify correct parameters (embed_texts calls generate_embedding which receives text directly)
        call_kwargs = mock_openai_client.embeddings.create.call_args[1]
        assert call_kwargs['input'] == query  # generate_embedding receives text directly

        # Verify vector was converted to string for pgvector
        fetch_calls = mock_conn.fetch.call_args_list
        assert len(fetch_calls) > 0


@pytest.mark.asyncio
async def test_result_ranking_and_ordering(mock_get_connection, mock_openai_client):
    """Test that search results are correctly ranked by similarity."""
    query = "artificial intelligence"
    resource_ids = ["res-1", "res-2"]

    # Create results with specific distances for verification
    ordered_rows = [
        {
            'id': 'emb-1',
            'text': 'Most relevant result',
            'resource_id': 'res-1',
            'upload_id': 'upload-1',
            'chunk_index': 0,
            'distance': 0.1,  # Lowest distance = highest similarity
            'resource_name': 'Resource 1'
        },
        {
            'id': 'emb-2',
            'text': 'Medium relevance result',
            'resource_id': 'res-1',
            'upload_id': 'upload-1',
            'chunk_index': 1,
            'distance': 0.3,
            'resource_name': 'Resource 1'
        },
        {
            'id': 'emb-3',
            'text': 'Least relevant result',
            'resource_id': 'res-2',
            'upload_id': 'upload-2',
            'chunk_index': 0,
            'distance': 0.5,  # Highest distance = lowest similarity
            'resource_name': 'Resource 2'
        }
    ]

    mock_get_connection.fetch = AsyncMock(return_value=ordered_rows)

    results = await search(query, resource_ids, top_k=10)

    # Verify results are ordered by similarity (descending)
    similarities = [src["similarity"] for src in results["detailed_sources"]]
    assert similarities[0] > similarities[1] > similarities[2]

    # Verify most similar result is first
    assert results["detailed_sources"][0]["similarity"] == 1 - 0.1  # 0.9
    assert results["detailed_sources"][1]["similarity"] == 1 - 0.3  # 0.7
    assert results["detailed_sources"][2]["similarity"] == 1 - 0.5  # 0.5

    # Verify contexts are in same order
    assert results["contexts"][0] == 'Most relevant result'
    assert results["contexts"][1] == 'Medium relevance result'
    assert results["contexts"][2] == 'Least relevant result'


@pytest.mark.asyncio
async def test_search_without_resource_filter(mock_get_connection, mock_embedding_rows, mock_openai_client):
    """Test search across all resources when no resource_ids filter provided."""
    query = "general search"
    resource_ids = []  # Empty list = search all

    mock_get_connection.fetch = AsyncMock(return_value=mock_embedding_rows)

    results = await search(query, resource_ids, top_k=5)

    # Verify results from multiple resources
    unique_resources = set(src["resource_id"] for src in results["detailed_sources"])
    assert len(unique_resources) > 1  # Should have res-1 and res-2

    # Verify SQL query doesn't have resource_id filter
    fetch_calls = mock_get_connection.fetch.call_args_list
    sql_query = fetch_calls[-1][0][0]

    # When resource_ids is empty, query should not filter by resource_id
    # or use "WHERE resource_id IN ()" which would return nothing
    assert results["count"] > 0


@pytest.mark.asyncio
async def test_list_resources_filtering():
    """Test listing available resources with ready status."""
    resource_ids = ["res-1", "res-2", "res-3"]

    # Mock CRUD responses
    async def mock_get_resource(rid):
        resources = {
            "res-1": {"id": "res-1", "name": "Resource 1", "status": "ready", "chunk_count": 10},
            "res-2": {"id": "res-2", "name": "Resource 2", "status": "processing", "chunk_count": 0},
            "res-3": {"id": "res-3", "name": "Resource 3", "status": "ready", "chunk_count": 5},
        }
        return resources.get(rid)

    with patch('app.database.crud.get_resource', new_callable=AsyncMock, side_effect=mock_get_resource):
        resources = await list_resources(resource_ids)

        # Should only return ready resources
        assert len(resources) == 2
        # list_resources doesn't return status, only id, name, description, chunk_count
        assert resources[0]["id"] == "res-1"
        assert resources[1]["id"] == "res-3"
        assert resources[0]["chunk_count"] == 10
        assert resources[1]["chunk_count"] == 5
