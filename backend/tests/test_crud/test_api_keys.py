"""Integration tests for api_keys CRUD module."""

import pytest
from app.database.crud import api_keys
from app.core.utils.encryption import encrypt_api_key



@pytest.mark.asyncio
async def test_create_api_key_encrypted(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test creating API key with encryption."""
    encrypted_key = encrypt_api_key("sk-test123")
    api_key_id = await api_keys.create_api_key(
        plain_value=encrypted_key,
        user_id=sample_user["id"],
        service_id=sample_service["id"]
    )

    assert api_key_id is not None
    assert api_key_id.startswith("key_")


@pytest.mark.asyncio
async def test_update_api_key(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test updating API key."""
    encrypted_key = encrypt_api_key("sk-old")
    api_key_id = await api_keys.create_api_key(
        plain_value=encrypted_key,
        user_id=sample_user["id"],
        service_id=sample_service["id"]
    )

    new_encrypted_key = encrypt_api_key("sk-new")
    success = await api_keys.update_api_key(api_key_id, new_encrypted_key)
    assert success is True


@pytest.mark.asyncio
async def test_delete_api_key(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test deleting API key."""
    encrypted_key = encrypt_api_key("sk-temp")
    api_key_id = await api_keys.create_api_key(
        plain_value=encrypted_key,
        user_id=sample_user["id"],
        service_id=sample_service["id"]
    )

    success = await api_keys.delete_api_key(api_key_id)
    assert success is True
