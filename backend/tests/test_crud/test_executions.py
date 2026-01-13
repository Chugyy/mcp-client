"""Integration tests for executions (automation) CRUD module."""

import pytest
from app.database.crud import executions



@pytest.fixture
async def sample_automation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Create sample automation for executions."""
    from app.database.crud import automations
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Sample Automation",
    )
    automation = await automations.get_automation(automation_id)
    return automation


@pytest.mark.asyncio
async def test_create_execution(clean_db, sample_automation, sample_user, mock_pool_for_crud):
    """Test creating an execution record."""
    execution_id = await executions.create_execution(
        automation_id=sample_automation["id"],
        user_id=sample_user["id"],
        status="running"
    )

    assert execution_id is not None


@pytest.mark.asyncio
async def test_get_execution(clean_db, sample_automation, sample_user, mock_pool_for_crud):
    """Test getting an execution."""
    execution_id = await executions.create_execution(
        automation_id=sample_automation["id"],
        user_id=sample_user["id"],
        status="running"
    )

    execution = await executions.get_execution(execution_id)
    assert execution is not None


@pytest.mark.asyncio
async def test_update_execution_status(clean_db, sample_automation, sample_user, mock_pool_for_crud):
    """Test updating execution status."""
    execution_id = await executions.create_execution(
        automation_id=sample_automation["id"],
        user_id=sample_user["id"],
        status="running"
    )

    success = await executions.update_execution_status(execution_id, "success")
    assert success is True


@pytest.mark.asyncio
async def test_list_executions_by_automation(clean_db, sample_automation, sample_user, mock_pool_for_crud):
    """Test listing executions by automation."""
    execution_id = await executions.create_execution(
        automation_id=sample_automation["id"],
        user_id=sample_user["id"],
        status="success"
    )

    executions_list = await executions.list_executions(sample_automation["id"])
    assert any(e["id"] == execution_id for e in executions_list)
