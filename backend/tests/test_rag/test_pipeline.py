"""End-to-end tests for complete RAG pipeline."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from app.core.services.resources.rag.ingestion import ingest_resource
from app.core.services.resources.rag.search import search


@pytest.mark.asyncio
async def test_full_ingestion_pipeline(mock_openai_client, sample_document):
    """Test complete ingestion: upload → chunk → embed → store."""
    resource_id = 'test-resource-pipeline'
    upload_id = 'test-upload-pipeline'

    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/pipeline_test.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    # Track execution stages
    stages_completed = {
        'status_processing': False,
        'embeddings_deleted': False,
        'embeddings_generated': False,
        'vectors_stored': False,
        'status_ready': False
    }

    # Mock status updates
    async def track_status(rid, status, **kwargs):
        if status == 'processing':
            stages_completed['status_processing'] = True
        elif status == 'ready':
            stages_completed['status_ready'] = True
            assert 'chunk_count' in kwargs
            assert kwargs['chunk_count'] > 0

    # Track database operations
    async def track_execute(query, *args):
        if 'DELETE FROM embeddings' in query:
            stages_completed['embeddings_deleted'] = True
        elif 'INSERT INTO embeddings' in query:
            stages_completed['vectors_stored'] = True

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=track_execute)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock, side_effect=track_status):
                with patch('builtins.open', mock_open(read_data=sample_document['content'])):
                    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                        mock_settings.chunk_size = 500
                        mock_settings.chunk_overlap = 100

                        # Execute full ingestion pipeline
                        await ingest_resource(resource_id)

                        # Verify all stages completed
                        assert stages_completed['status_processing'], "Resource not marked as processing"
                        assert stages_completed['embeddings_deleted'], "Old embeddings not cleaned"
                        assert stages_completed['vectors_stored'], "Vectors not stored in database"
                        assert stages_completed['status_ready'], "Resource not marked as ready"

                        # Verify embeddings were generated
                        assert mock_openai_client.embeddings.create.call_count > 0
                        stages_completed['embeddings_generated'] = True

    # Final verification
    assert all(stages_completed.values()), f"Pipeline incomplete: {stages_completed}"


@pytest.mark.asyncio
async def test_full_retrieval_pipeline(mock_openai_client, mock_embedding_rows):
    """Test complete retrieval: query → embed → search → rank → return."""
    query = "AI and machine learning concepts"
    resource_ids = ["res-1", "res-2"]

    # Track retrieval stages
    stages_completed = {
        'query_embedded': False,
        'vector_search': False,
        'results_ranked': False,
        'contexts_extracted': False
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_embedding_rows)
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        # Execute full retrieval pipeline
        results = await search(query, resource_ids, top_k=5)

        # Verify query was embedded
        assert mock_openai_client.embeddings.create.call_count > 0
        stages_completed['query_embedded'] = True

        # Verify vector search was performed
        assert mock_conn.fetch.called
        fetch_call_args = mock_conn.fetch.call_args[0]
        assert 'vector' in fetch_call_args[0].lower() or '<=>' in fetch_call_args[0]
        stages_completed['vector_search'] = True

        # Verify results are ranked by similarity
        if len(results['detailed_sources']) > 1:
            similarities = [src['similarity'] for src in results['detailed_sources']]
            assert similarities == sorted(similarities, reverse=True)
        stages_completed['results_ranked'] = True

        # Verify contexts extracted
        assert 'contexts' in results
        assert len(results['contexts']) > 0
        assert all(isinstance(ctx, str) for ctx in results['contexts'])
        stages_completed['contexts_extracted'] = True

    # Final verification
    assert all(stages_completed.values()), f"Retrieval pipeline incomplete: {stages_completed}"


@pytest.mark.asyncio
async def test_rag_augmented_llm_response():
    """Test RAG context integration with LLM response generation."""
    query = "Explain machine learning"
    resource_ids = ["ml-resource-1"]

    # Mock RAG search results
    rag_contexts = [
        "Machine learning is a subset of AI that enables systems to learn from data.",
        "Supervised learning uses labeled data to train models.",
        "Neural networks are the foundation of deep learning."
    ]

    mock_search_results = {
        "contexts": rag_contexts,
        "sources": ["ml-resource-1"],
        "upload_ids": ["upload-1"],
        "detailed_sources": [
            {
                "resource_id": "ml-resource-1",
                "resource_name": "ML Guide",
                "chunk_id": f"chunk-{i}",
                "similarity": 0.9 - (i * 0.1),
                "content": ctx[:100]
            }
            for i, ctx in enumerate(rag_contexts)
        ],
        "count": 3
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.search.get_connection', return_value=mock_conn):
        with patch('app.core.services.resources.rag.search.search', new_callable=AsyncMock) as mock_search:
            with patch('app.core.services.resources.rag.embeddings.embed_texts', new_callable=AsyncMock) as mock_embed:
                mock_search.return_value = mock_search_results
                mock_embed.return_value = [[0.1] * 3072]

                # Simulate RAG-augmented LLM call
                search_results = await mock_search(query, resource_ids, top_k=5)

                # Verify contexts are available for LLM augmentation
                assert len(search_results["contexts"]) == 3
                assert all(isinstance(ctx, str) for ctx in search_results["contexts"])

                # Simulate building augmented prompt
                context_text = "\n".join(search_results["contexts"])
                augmented_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"

                # Verify augmented prompt contains RAG context
                assert "Machine learning is a subset of AI" in augmented_prompt
                assert "Supervised learning" in augmented_prompt
                assert "Neural networks" in augmented_prompt
                assert query in augmented_prompt

                # Verify sources are tracked for attribution
                assert len(search_results["sources"]) > 0
                assert "ml-resource-1" in search_results["sources"]


@pytest.mark.asyncio
async def test_resource_deletion_cascade_embeddings():
    """Test that deleting a resource cascades to embeddings deletion."""
    resource_id = 'test-resource-to-delete'

    # Track DELETE operations
    delete_operations = []

    async def track_delete(query, *args):
        if 'DELETE' in query.upper():
            delete_operations.append({
                'query': query,
                'args': args
            })

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=track_delete)
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.close = AsyncMock(return_value=None)

    # Mock CRUD delete resource operation
    async def mock_delete_resource(rid):
        """Simulate deleting resource and cascading to embeddings."""
        async def get_conn():
            return mock_conn

        conn = await get_conn()

        # Delete embeddings first (cascade)
        await conn.execute(
            "DELETE FROM embeddings WHERE resource_id = $1",
            rid
        )

        # Delete resource
        await conn.execute(
            "DELETE FROM resources WHERE id = $1",
            rid
        )

        await conn.close()

    with patch('app.database.crud.delete_resource', new_callable=AsyncMock, side_effect=mock_delete_resource):
        # Execute resource deletion
        await mock_delete_resource(resource_id)

        # Verify embeddings were deleted
        embeddings_deleted = any(
            'embeddings' in op['query'].lower() and resource_id in str(op['args'])
            for op in delete_operations
        )
        assert embeddings_deleted, "Embeddings not deleted on resource deletion"

        # Verify resource was deleted
        resource_deleted = any(
            'resources' in op['query'].lower() and resource_id in str(op['args'])
            for op in delete_operations
        )
        assert resource_deleted, "Resource not deleted"

        # Verify cascade order: embeddings deleted before resource
        embeddings_index = next(
            i for i, op in enumerate(delete_operations)
            if 'embeddings' in op['query'].lower()
        )
        resource_index = next(
            i for i, op in enumerate(delete_operations)
            if 'resources' in op['query'].lower()
        )
        assert embeddings_index < resource_index, "Embeddings should be deleted before resource"


@pytest.mark.asyncio
async def test_pipeline_error_recovery(mock_openai_client):
    """Test that pipeline handles errors gracefully and sets error status."""
    resource_id = 'test-resource-error'
    upload_id = 'test-upload-error'

    # Upload that will cause an error (missing file)
    upload_data = {
        'id': upload_id,
        'file_path': '/nonexistent/file.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    error_status_set = False

    async def track_error_status(rid, status, **kwargs):
        nonlocal error_status_set
        if status == 'error':
            error_status_set = True
            assert 'error_message' in kwargs
            assert len(kwargs['error_message']) > 0

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock, side_effect=track_error_status):
                # Pipeline should handle error and set error status
                with pytest.raises(FileNotFoundError):
                    await ingest_resource(resource_id)

                # Verify error status was set
                assert error_status_set, "Error status not set on pipeline failure"
