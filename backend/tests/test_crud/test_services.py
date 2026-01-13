"""Integration tests for services (LLM) CRUD module."""

import pytest
from app.database.crud import services



@pytest.mark.asyncio
async def test_create_service(clean_db, mock_pool_for_crud):
    """Test creating an LLM service."""
    service_id = await services.create_service(
        name="OpenAI",
        provider="openai",
        description="OpenAI API service"
    )

    assert service_id is not None
    assert service_id.startswith("svc_")

    service = await services.get_service(service_id)
    assert service["name"] == "OpenAI"
    assert service["provider"] == "openai"


@pytest.mark.asyncio
async def test_get_service_by_code(clean_db, sample_service, mock_pool_for_crud):
    """Test getting service by ID."""
    service = await services.get_service(sample_service["id"])

    assert service is not None
    assert service["id"] == sample_service["id"]


@pytest.mark.asyncio
async def test_update_service(clean_db, sample_service, mock_pool_for_crud):
    """Test updating service."""
    success = await services.update_service(
        sample_service["id"],
        name="Updated Service",
        description="Updated description"
    )
    assert success is True

    service = await services.get_service(sample_service["id"])
    assert service["name"] == "Updated Service"


@pytest.mark.asyncio
async def test_delete_service(clean_db, sample_service, mock_pool_for_crud):
    """Test deleting service."""
    success = await services.delete_service(sample_service["id"])
    assert success is True

    service = await services.get_service(sample_service["id"])
    assert service is None


@pytest.mark.asyncio
async def test_list_services(clean_db, sample_service, mock_pool_for_crud):
    """Test listing all services."""
    services_list = await services.list_services()

    assert isinstance(services_list, list)
    assert any(s["id"] == sample_service["id"] for s in services_list)
