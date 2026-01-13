"""Integration tests for agents CRUD module."""

import pytest
from app.database.crud import agents



@pytest.mark.asyncio
async def test_create_agent_success(clean_db, sample_user, mock_pool_for_crud):
    """Test creating agent with valid data."""
    agent_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Test Agent",
        system_prompt="You are a helpful assistant",
        description="A test agent",
        tags=["test", "helper"]
    )

    # Verify agent was created
    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert agent_id.startswith("agt_")

    # Fetch and verify agent data
    agent = await agents.get_agent(agent_id)
    assert agent["name"] == "Test Agent"
    assert agent["system_prompt"] == "You are a helpful assistant"
    assert agent["description"] == "A test agent"
    assert agent["tags"] == ["test", "helper"]
    assert agent["user_id"] == sample_user["id"]
    assert agent["enabled"] is True


@pytest.mark.asyncio
async def test_create_agent_with_tags_normalization(clean_db, sample_user, mock_pool_for_crud):
    """Test creating agent with tags that may need normalization."""
    agent_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Tagged Agent",
        system_prompt="Test prompt",
        tags=["Python", "AI", "Automation"]
    )

    agent = await agents.get_agent(agent_id)
    assert agent is not None
    assert isinstance(agent["tags"], list)
    assert len(agent["tags"]) == 3
    assert "Python" in agent["tags"]
    assert "AI" in agent["tags"]
    assert "Automation" in agent["tags"]


@pytest.mark.asyncio
async def test_create_agent_without_tags(clean_db, sample_user, mock_pool_for_crud):
    """Test creating agent without tags defaults to empty array."""
    agent_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="No Tags Agent",
        system_prompt="Test prompt"
    )

    agent = await agents.get_agent(agent_id)
    assert agent["tags"] == []


@pytest.mark.asyncio
async def test_get_agent_by_id(clean_db, sample_agent, mock_pool_for_crud):
    """Test getting agent by ID."""
    agent = await agents.get_agent(sample_agent["id"])

    assert agent is not None
    assert agent["id"] == sample_agent["id"]
    assert agent["name"] == sample_agent["name"]


@pytest.mark.asyncio
async def test_get_agent_by_id_not_found(clean_db, mock_pool_for_crud):
    """Test getting non-existent agent returns None."""
    agent = await agents.get_agent("agt_nonexistent123")
    assert agent is None


@pytest.mark.asyncio
async def test_get_agent_by_name(clean_db, sample_agent, mock_pool_for_crud):
    """Test getting agent by name."""
    agent = await agents.get_agent_by_name(sample_agent["name"])

    assert agent is not None
    assert agent["id"] == sample_agent["id"]
    assert agent["name"] == sample_agent["name"]


@pytest.mark.asyncio
async def test_get_agents_by_user(clean_db, sample_user, mock_pool_for_crud):
    """Test getting all agents for a user."""
    # Create multiple agents for user
    agent1_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Agent 1",
        system_prompt="Prompt 1"
    )
    agent2_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Agent 2",
        system_prompt="Prompt 2"
    )

    user_agents = await agents.list_agents_by_user(sample_user["id"])

    assert len(user_agents) >= 2
    assert any(a["id"] == agent1_id for a in user_agents)
    assert any(a["id"] == agent2_id for a in user_agents)


@pytest.mark.asyncio
async def test_update_agent_partial(clean_db, sample_agent, mock_pool_for_crud):
    """Test updating agent with partial data."""
    success = await agents.update_agent(
        sample_agent["id"],
        name="Updated Agent Name"
    )
    assert success is True

    # Verify update
    agent = await agents.get_agent(sample_agent["id"])
    assert agent["name"] == "Updated Agent Name"
    # Other fields should remain unchanged
    assert agent["system_prompt"] == sample_agent["system_prompt"]


@pytest.mark.asyncio
async def test_update_agent_multiple_fields(clean_db, sample_agent, mock_pool_for_crud):
    """Test updating multiple agent fields."""
    success = await agents.update_agent(
        sample_agent["id"],
        name="New Name",
        description="New description",
        tags=["updated", "tags"]
    )
    assert success is True

    # Verify updates
    agent = await agents.get_agent(sample_agent["id"])
    assert agent["name"] == "New Name"
    assert agent["description"] == "New description"
    assert agent["tags"] == ["updated", "tags"]


@pytest.mark.asyncio
async def test_update_agent_enabled_status(clean_db, sample_agent, mock_pool_for_crud):
    """Test toggling agent enabled status."""
    # Disable agent
    success = await agents.update_agent(
        sample_agent["id"],
        enabled=False
    )
    assert success is True

    agent = await agents.get_agent(sample_agent["id"])
    assert agent["enabled"] is False

    # Re-enable agent
    success = await agents.update_agent(
        sample_agent["id"],
        enabled=True
    )
    assert success is True

    agent = await agents.get_agent(sample_agent["id"])
    assert agent["enabled"] is True


@pytest.mark.asyncio
async def test_delete_agent_success(clean_db, sample_agent, mock_pool_for_crud):
    """Test deleting agent."""
    success = await agents.delete_agent(sample_agent["id"])
    assert success is True

    # Verify deletion
    agent = await agents.get_agent(sample_agent["id"])
    assert agent is None


@pytest.mark.asyncio
async def test_delete_agent_not_found(clean_db, mock_pool_for_crud):
    """Test deleting non-existent agent returns False."""
    success = await agents.delete_agent("agt_nonexistent123")
    assert success is False


@pytest.mark.asyncio
async def test_list_agents_with_filters_enabled(clean_db, sample_user, mock_pool_for_crud):
    """Test listing agents with enabled/disabled filter."""
    # Create enabled and disabled agents
    enabled_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Enabled Agent",
        system_prompt="Prompt",
        enabled=True
    )
    disabled_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Disabled Agent",
        system_prompt="Prompt",
        enabled=False
    )

    # Get all agents
    all_agents = await agents.list_agents_by_user(sample_user["id"])

    # Verify both exist in list
    assert any(a["id"] == enabled_id and a["enabled"] is True for a in all_agents)
    assert any(a["id"] == disabled_id and a["enabled"] is False for a in all_agents)


@pytest.mark.asyncio
async def test_count_agents_by_user(clean_db, sample_user, mock_pool_for_crud):
    """Test counting agents for a user."""
    # Initially no agents (except possibly sample_agent if used)
    initial_count = await agents.count_agents_by_user(sample_user["id"])

    # Create agents
    await agents.create_agent(
        user_id=sample_user["id"],
        name="Agent 1",
        system_prompt="Prompt"
    )
    await agents.create_agent(
        user_id=sample_user["id"],
        name="Agent 2",
        system_prompt="Prompt"
    )

    # Verify count increased
    final_count = await agents.count_agents_by_user(sample_user["id"])
    assert final_count == initial_count + 2


@pytest.mark.asyncio
async def test_get_agent_by_name_and_user(clean_db, sample_agent, mock_pool_for_crud):
    """Test getting agent by name and user (uniqueness check)."""
    agent = await agents.get_agent_by_name_and_user(
        sample_agent["name"],
        sample_agent["user_id"]
    )

    assert agent is not None
    assert agent["id"] == sample_agent["id"]
    assert agent["name"] == sample_agent["name"]
    assert agent["user_id"] == sample_agent["user_id"]
