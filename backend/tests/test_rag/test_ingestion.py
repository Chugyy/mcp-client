"""Tests for RAG document ingestion pipeline."""

import pytest
import os
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from app.core.services.resources.rag.ingestion import ingest_resource
from app.core.services.resources.rag.chunking import chunk_text, chunk_document


@pytest.mark.asyncio
async def test_document_chunking_by_character_count():
    """Test document chunking with configurable chunk size."""
    text = "A" * 1000  # 1000 character text

    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
        mock_settings.chunk_size = 200
        mock_settings.chunk_overlap = 50

        chunks = chunk_text(text)

        # Verify chunking
        assert len(chunks) > 0
        assert all(len(chunk) <= 200 for chunk in chunks)

        # First chunk should be exactly 200 chars
        assert len(chunks[0]) == 200

        # Verify overlap by checking that chunks share content
        if len(chunks) > 1:
            # Second chunk starts at position 150 (200 - 50 overlap)
            overlap_start = 150
            assert chunks[0][overlap_start:] == chunks[1][:50]


@pytest.mark.asyncio
async def test_chunk_overlap_handling():
    """Test that chunk overlap is correctly applied."""
    text = "The quick brown fox jumps over the lazy dog. " * 50  # ~2250 chars

    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
        mock_settings.chunk_size = 500
        mock_settings.chunk_overlap = 100

        chunks = chunk_text(text)

        # Verify overlap exists between consecutive chunks
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Last 100 chars of current should overlap with start of next
            overlap_region = current_chunk[-100:]
            assert overlap_region in next_chunk[:100] or next_chunk.startswith(overlap_region[:50])


@pytest.mark.asyncio
async def test_metadata_extraction_from_upload():
    """Test metadata extraction during document chunking."""
    upload_data = {
        'id': 'test-upload-123',
        'file_path': '/tmp/test_doc.txt',
        'mime_type': 'text/plain',
        'title': 'Test Document',
        'metadata': {
            'author': 'Test Author',
            'date': '2026-01-06'
        }
    }

    test_content = "This is test content for metadata extraction. " * 10

    with patch('app.database.crud.get_upload', new_callable=AsyncMock) as mock_get_upload:
        with patch('builtins.open', mock_open(read_data=test_content)):
            with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                mock_settings.chunk_size = 100
                mock_settings.chunk_overlap = 20

                mock_get_upload.return_value = upload_data

                chunks = await chunk_document('test-upload-123')

                # Verify chunks were created
                assert len(chunks) > 0
                assert all(isinstance(chunk, str) for chunk in chunks)

                # Verify upload was retrieved
                mock_get_upload.assert_called_once_with('test-upload-123')


@pytest.mark.asyncio
async def test_embedding_generation_for_chunks(mock_openai_client):
    """Test that embeddings are generated for all chunks during ingestion."""
    resource_id = 'test-resource-id'
    upload_id = 'test-upload-id'

    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/test.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    test_content = "Content for embedding generation. " * 20

    # Mock database operations
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock):
                with patch('builtins.open', mock_open(read_data=test_content)):
                    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                        mock_settings.chunk_size = 100
                        mock_settings.chunk_overlap = 20

                        await ingest_resource(resource_id)

                        # Verify embeddings were generated
                        assert mock_openai_client.embeddings.create.call_count > 0

                        # Verify vectors were stored in database
                        assert mock_conn.execute.call_count > 0


@pytest.mark.asyncio
async def test_vector_storage_in_pgvector(mock_openai_client):
    """Test that vectors are correctly stored in pgvector format."""
    resource_id = 'test-resource-id'
    upload_id = 'test-upload-id'

    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/test.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    test_content = "Vector storage test content."

    # Track execute calls to verify INSERT statements
    execute_calls = []

    async def track_execute(query, *args):
        execute_calls.append((query, args))

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=track_execute)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock):
                with patch('builtins.open', mock_open(read_data=test_content)):
                    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                        mock_settings.chunk_size = 100
                        mock_settings.chunk_overlap = 20

                        await ingest_resource(resource_id)

                        # Verify INSERT into embeddings table
                        insert_calls = [call for call in execute_calls if 'INSERT INTO embeddings' in call[0]]
                        assert len(insert_calls) > 0

                        # Verify vector format (::halfvec cast)
                        assert any('::halfvec' in call[0] for call in insert_calls)


@pytest.mark.asyncio
async def test_duplicate_document_reindexing(mock_openai_client):
    """Test that re-ingesting a resource cleans old embeddings first."""
    resource_id = 'test-resource-id'
    upload_id = 'test-upload-id'

    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/test.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    test_content = "Duplicate test content."

    # Track DELETE calls
    delete_calls = []

    async def track_execute(query, *args):
        if 'DELETE' in query:
            delete_calls.append((query, args))

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=track_execute)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock):
                with patch('builtins.open', mock_open(read_data=test_content)):
                    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                        mock_settings.chunk_size = 100
                        mock_settings.chunk_overlap = 20

                        await ingest_resource(resource_id)

                        # Verify old embeddings were deleted
                        assert len(delete_calls) > 0
                        assert any('DELETE FROM embeddings' in call[0] for call in delete_calls)
                        assert any(resource_id in str(call[1]) for call in delete_calls)


@pytest.mark.asyncio
async def test_ingestion_error_handling_corrupt_file():
    """Test error handling for corrupt or unsupported files."""
    resource_id = 'test-resource-id'
    upload_id = 'test-upload-id'

    # Upload with unsupported mime type
    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/test.unknown',
        'mime_type': 'application/octet-stream',  # Unsupported
        'resource_id': resource_id
    }

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock) as mock_update:
                # Should raise ValueError for unsupported mime type
                with pytest.raises(ValueError) as exc_info:
                    await ingest_resource(resource_id)

                assert "Unsupported mime_type" in str(exc_info.value)

                # Verify resource status was set to 'error'
                error_calls = [
                    call for call in mock_update.call_args_list
                    if len(call[0]) > 1 and call[0][1] == 'error'
                ]
                assert len(error_calls) > 0


@pytest.mark.asyncio
async def test_ingestion_status_transitions(mock_openai_client):
    """Test that resource status transitions correctly during ingestion."""
    resource_id = 'test-resource-id'
    upload_id = 'test-upload-id'

    upload_data = {
        'id': upload_id,
        'file_path': '/tmp/test.txt',
        'mime_type': 'text/plain',
        'resource_id': resource_id
    }

    test_content = "Status transition test content."

    status_calls = []

    async def track_status(rid, status, **kwargs):
        status_calls.append((rid, status, kwargs))

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[upload_data])
    mock_conn.close = AsyncMock(return_value=None)

    with patch('app.core.services.resources.rag.ingestion.get_connection', return_value=mock_conn):
        with patch('app.database.crud.get_upload', new_callable=AsyncMock, return_value=upload_data):
            with patch('app.database.crud.update_resource_status', new_callable=AsyncMock, side_effect=track_status):
                with patch('builtins.open', mock_open(read_data=test_content)):
                    with patch('app.core.services.resources.rag.chunking.settings') as mock_settings:
                        mock_settings.chunk_size = 100
                        mock_settings.chunk_overlap = 20

                        await ingest_resource(resource_id)

                        # Verify status transitions: processing -> ready
                        assert len(status_calls) == 2
                        assert status_calls[0][1] == 'processing'
                        assert status_calls[1][1] == 'ready'
                        assert 'chunk_count' in status_calls[1][2]
