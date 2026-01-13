"""Integration tests for workflow_steps CRUD module."""

import pytest
from app.database.crud import automations



@pytest.fixture
async def sample_automation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Create sample automation for workflow steps."""
    automation_id = await automations.create_automation(
        user_id=sample_user["id"],
        name="Sample Automation",
    )
    automation = await automations.get_automation(automation_id)
    return automation


@pytest.mark.asyncio
async def test_create_workflow_step(clean_db, sample_automation, mock_pool_for_crud):
    """Test creating a workflow step."""
    step_id = await automations.create_workflow_step(
        automation_id=sample_automation["id"],
        step_order=1,
        step_name="Test Step",
        step_type="action",
        step_subtype="api_call"
    )

    assert step_id is not None


@pytest.mark.asyncio
async def test_get_workflow_step(clean_db, sample_automation, mock_pool_for_crud):
    """Test getting a workflow step."""
    step_id = await automations.create_workflow_step(
        automation_id=sample_automation["id"],
        step_order=1,
        step_name="Test Step",
        step_type="control",
        step_subtype="if_then"
    )

    step = await automations.get_workflow_step(step_id)
    assert step is not None


@pytest.mark.asyncio
async def test_list_workflow_steps_by_automation(clean_db, sample_automation, mock_pool_for_crud):
    """Test listing workflow steps by automation."""
    step_id = await automations.create_workflow_step(
        automation_id=sample_automation["id"],
        step_order=1,
        step_name="Test Step",
        step_type="action",
        step_subtype="api_call"
    )

    steps_list = await automations.list_workflow_steps(sample_automation["id"])
    assert any(s["id"] == step_id for s in steps_list)
