"""Integration tests for resources CRUD module."""

import pytest
from app.database.crud import resources



@pytest.mark.asyncio
async def test_create_resource(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test creating a resource."""
    resource_id = await resources.create_resource(
        user_id=sample_user["id"],
        name="Test Resource"
    )

    assert resource_id is not None
    assert resource_id.startswith("res_")

    resource = await resources.get_resource(resource_id)
    assert resource["name"] == "Test Resource"


@pytest.mark.asyncio
async def test_get_resource_by_id(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test getting resource by ID."""
    resource_id = await resources.create_resource(
        user_id=sample_user["id"],
        name="Test"
    )

    resource = await resources.get_resource(resource_id)
    assert resource is not None


@pytest.mark.asyncio
async def test_update_resource(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test updating resource."""
    resource_id = await resources.create_resource(
        user_id=sample_user["id"],
        name="Original"
    )

    success = await resources.update_resource(
        resource_id,
        name="Updated Name"
    )
    assert success is True


@pytest.mark.asyncio
async def test_delete_resource(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test deleting resource."""
    resource_id = await resources.create_resource(
        user_id=sample_user["id"],
        name="Temp"
    )

    success = await resources.delete_resource(resource_id)
    assert success is True
