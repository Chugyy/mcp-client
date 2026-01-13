"""Integration tests for automations CRUD module."""

import pytest
from app.database.crud import automations



@pytest.mark.asyncio
async def test_create_automation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test creating automation."""
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Test Automation",
    )

    assert automation_id is not None
    assert automation_id.startswith("auto_")


@pytest.mark.asyncio
async def test_get_automation_by_id(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test getting automation by ID."""
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Get Test",
    )

    automation = await automations.get_automation(automation_id)
    assert automation is not None


@pytest.mark.asyncio
async def test_update_automation_config(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test updating automation configuration."""
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Update Test",
    )

    success = await automations.update_automation(
        automation_id,
        description="Updated description"
    )
    assert success is True


@pytest.mark.asyncio
async def test_delete_automation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test deleting automation."""
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Delete Test",
    )

    success = await automations.delete_automation(automation_id)
    assert success is True
