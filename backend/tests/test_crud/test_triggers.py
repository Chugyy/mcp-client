"""Integration tests for triggers CRUD module."""

import pytest
from app.database.crud import triggers



@pytest.fixture
async def sample_automation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Create sample automation for triggers."""
    from app.database.crud import automations
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Sample Automation",
    )
    automation = await automations.get_automation(automation_id)
    return automation


@pytest.mark.asyncio
async def test_create_trigger(clean_db, sample_automation, mock_pool_for_crud):
    """Test creating a trigger."""
    trigger_id = await triggers.create_trigger(
        automation_id=sample_automation["id"],
        trigger_type="manual",
        config={}
    )

    assert trigger_id is not None


@pytest.mark.asyncio
async def test_get_trigger(clean_db, sample_automation, mock_pool_for_crud):
    """Test getting a trigger."""
    trigger_id = await triggers.create_trigger(
        automation_id=sample_automation["id"],
        trigger_type="manual",
        config={}
    )

    trigger = await triggers.get_trigger(trigger_id)
    assert trigger is not None


@pytest.mark.asyncio
async def test_delete_trigger(clean_db, sample_automation, mock_pool_for_crud):
    """Test deleting a trigger."""
    trigger_id = await triggers.create_trigger(
        automation_id=sample_automation["id"],
        trigger_type="manual",
        config={}
    )

    success = await triggers.delete_trigger(trigger_id)
    assert success is True


@pytest.mark.asyncio
async def test_list_triggers_by_automation(clean_db, sample_automation, mock_pool_for_crud):
    """Test listing triggers by automation."""
    trigger_id = await triggers.create_trigger(
        automation_id=sample_automation["id"],
        trigger_type="manual",
        config={}
    )

    triggers_list = await triggers.get_triggers(sample_automation["id"])
    assert any(t["id"] == trigger_id for t in triggers_list)
