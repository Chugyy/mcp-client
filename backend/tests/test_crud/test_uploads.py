"""Integration tests for uploads CRUD module."""

import pytest
from app.database.crud import uploads



@pytest.mark.asyncio
async def test_create_upload_record(clean_db, sample_user, mock_pool_for_crud):
    """Test creating upload record."""
    upload_id = await uploads.create_upload(
        user_id=sample_user["id"],
        filename="test.txt",
        file_path="/uploads/test.txt",
        file_size=1024,
        mime_type="text/plain"
    )

    assert upload_id is not None
    assert upload_id.startswith("upl_")

    upload = await uploads.get_upload(upload_id)
    assert upload["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_get_upload_by_id(clean_db, sample_user, mock_pool_for_crud):
    """Test getting upload by ID."""
    upload_id = await uploads.create_upload(
        user_id=sample_user["id"],
        filename="doc.pdf",
        file_path="/uploads/doc.pdf",
        file_size=2048,
        mime_type="application/pdf"
    )

    upload = await uploads.get_upload(upload_id)
    assert upload is not None


@pytest.mark.asyncio
async def test_delete_upload_success(clean_db, sample_user, mock_pool_for_crud):
    """Test deleting upload by ID."""
    upload_id = await uploads.create_upload(
        user_id=sample_user["id"],
        filename="file.txt",
        file_path="/uploads/file.txt",
        file_size=512,
        mime_type="text/plain"
    )

    success = await uploads.delete_upload(upload_id)
    assert success is True

    # Verify deletion
    upload = await uploads.get_upload(upload_id)
    assert upload is None


@pytest.mark.asyncio
async def test_delete_upload(clean_db, sample_user, mock_pool_for_crud):
    """Test deleting upload."""
    upload_id = await uploads.create_upload(
        user_id=sample_user["id"],
        filename="temp.txt",
        file_path="/uploads/temp.txt",
        file_size=100,
        mime_type="text/plain"
    )

    success = await uploads.delete_upload(upload_id)
    assert success is True


@pytest.mark.asyncio
async def test_list_uploads_by_user(clean_db, sample_user, mock_pool_for_crud):
    """Test listing uploads by user."""
    upload_id = await uploads.create_upload(
        user_id=sample_user["id"],
        filename="user_file.txt",
        file_path="/uploads/user_file.txt",
        file_size=256,
        mime_type="text/plain"
    )

    uploads_list = await uploads.list_uploads_by_user(sample_user["id"])
    assert any(u["id"] == upload_id for u in uploads_list)
