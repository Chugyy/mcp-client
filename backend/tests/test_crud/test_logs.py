"""Integration tests for logs CRUD module."""

import pytest
from app.database.crud import logs



@pytest.mark.asyncio
async def test_create_log(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test creating a log entry."""
    log_id = await logs.create_log(
        user_id=sample_user["id"],
        log_type="validation",
        data={"message": "Test log message"},
        agent_id=sample_agent["id"]
    )

    assert log_id is not None


@pytest.mark.asyncio
async def test_get_log_by_id(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test getting log by ID."""
    log_id = await logs.create_log(
        user_id=sample_user["id"],
        log_type="stream_stop",
        data={"message": "Warning message"},
        agent_id=sample_agent["id"]
    )

    log = await logs.get_log(log_id)
    assert log is not None


@pytest.mark.asyncio
async def test_list_logs_by_user(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test listing logs by user."""
    log_id = await logs.create_log(
        user_id=sample_user["id"],
        log_type="error",
        data={"message": "Debug message"},
        agent_id=sample_agent["id"]
    )

    logs_list = await logs.list_logs_by_user(sample_user["id"])
    assert any(l["id"] == log_id for l in logs_list)
