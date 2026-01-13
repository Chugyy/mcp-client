"""Integration tests for user_providers CRUD module."""

import pytest
from app.database.crud import user_providers
from app.core.utils.encryption import encrypt_api_key



@pytest.mark.asyncio
async def test_create_user_provider(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test creating user provider."""
    provider_id = await user_providers.create_user_provider(
        user_id=sample_user["id"],
        service_id=sample_service["id"],
        api_key_id=None
    )

    assert provider_id is not None


@pytest.mark.asyncio
async def test_get_provider_by_user_service(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test getting provider by user and service."""
    await user_providers.create_user_provider(
        user_id=sample_user["id"],
        service_id=sample_service["id"],
        api_key_id=None
    )

    provider = await user_providers.get_user_provider_by_service(sample_user["id"], sample_service["id"])
    assert provider is not None


@pytest.mark.asyncio
async def test_update_provider_credentials(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test updating provider credentials."""
    provider_id = await user_providers.create_user_provider(
        user_id=sample_user["id"],
        service_id=sample_service["id"],
        api_key_id=None
    )

    success = await user_providers.update_user_provider(
        provider_id,
        enabled=False
    )
    assert success is True


@pytest.mark.asyncio
async def test_delete_provider(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test deleting provider."""
    provider_id = await user_providers.create_user_provider(
        user_id=sample_user["id"],
        service_id=sample_service["id"],
        api_key_id=None
    )

    success = await user_providers.delete_user_provider(provider_id)
    assert success is True


@pytest.mark.asyncio
async def test_list_providers_by_user(clean_db, sample_user, sample_service, mock_pool_for_crud):
    """Test listing providers by user."""
    provider_id = await user_providers.create_user_provider(
        user_id=sample_user["id"],
        service_id=sample_service["id"],
        api_key_id=None
    )

    providers_list = await user_providers.list_user_providers(sample_user["id"])
    assert any(p["id"] == provider_id for p in providers_list)
