"""Integration tests for validations CRUD module."""

import pytest
from app.database.crud import validations



@pytest.mark.asyncio
async def test_create_validation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test creating a validation request."""
    validation_id = await validations.create_validation(
        user_id=sample_user["id"],
        agent_id=sample_agent["id"],
        title="test_tool",
        source="test", process="test_process"
    )

    assert validation_id is not None


@pytest.mark.asyncio
async def test_get_validation_by_id(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test getting validation by ID."""
    validation_id = await validations.create_validation(
        user_id=sample_user["id"],
        agent_id=sample_agent["id"],
        title="get_test",
        source="test", process="test_process"
    )

    validation = await validations.get_validation(validation_id)
    assert validation is not None


@pytest.mark.asyncio
async def test_update_validation_status(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test updating validation status."""
    validation_id = await validations.create_validation(
        user_id=sample_user["id"],
        agent_id=sample_agent["id"],
        title="update_test",
        source="test", process="test_process"
    )

    success = await validations.update_validation_status(validation_id, "approved")
    assert success is True


@pytest.mark.asyncio
async def test_list_validations_by_user(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test listing validations by user."""
    validation_id = await validations.create_validation(
        user_id=sample_user["id"],
        agent_id=sample_agent["id"],
        title="list_test",
        source="test", process="test_process"
    )

    validations_list = await validations.list_validations_by_user(sample_user["id"])
    assert any(v["id"] == validation_id for v in validations_list)


@pytest.mark.asyncio
async def test_delete_validation(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test deleting validation."""
    validation_id = await validations.create_validation(
        user_id=sample_user["id"],
        agent_id=sample_agent["id"],
        title="delete_test",
        source="test", process="test_process"
    )

    success = await validations.delete_validation(validation_id)
    assert success is True
