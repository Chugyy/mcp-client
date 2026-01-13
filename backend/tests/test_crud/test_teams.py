"""Integration tests for teams CRUD module."""

import pytest
from app.database.crud import teams



@pytest.mark.asyncio
async def test_create_team(clean_db, mock_pool_for_crud):
    """Test creating a team."""
    team_id = await teams.create_team(
        name="Test Team",
        system_prompt="Team system prompt",
        description="A test team"
    )

    assert team_id is not None
    assert team_id.startswith("tem_")

    team = await teams.get_team(team_id)
    assert team["name"] == "Test Team"
    assert team["system_prompt"] == "Team system prompt"


@pytest.mark.asyncio
async def test_get_team_by_id(clean_db, sample_team, mock_pool_for_crud):
    """Test getting team by ID."""
    team = await teams.get_team(sample_team["id"])

    assert team is not None
    assert team["id"] == sample_team["id"]
    assert team["name"] == sample_team["name"]


@pytest.mark.asyncio
async def test_update_team_configuration(clean_db, sample_team, mock_pool_for_crud):
    """Test updating team configuration."""
    success = await teams.update_team(
        sample_team["id"],
        name="Updated Team Name",
        description="Updated description"
    )
    assert success is True

    team = await teams.get_team(sample_team["id"])
    assert team["name"] == "Updated Team Name"
    assert team["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_team(clean_db, sample_team, mock_pool_for_crud):
    """Test deleting a team."""
    success = await teams.delete_team(sample_team["id"])
    assert success is True

    team = await teams.get_team(sample_team["id"])
    assert team is None


@pytest.mark.asyncio
async def test_list_teams(clean_db, sample_team, mock_pool_for_crud):
    """Test listing all teams."""
    teams_list = await teams.list_teams()

    assert isinstance(teams_list, list)
    assert len(teams_list) >= 1
    assert any(t["id"] == sample_team["id"] for t in teams_list)


@pytest.mark.asyncio
async def test_list_teams_enabled_only(clean_db, mock_pool_for_crud):
    """Test listing only enabled teams."""
    # Create enabled and disabled teams
    enabled_id = await teams.create_team(
        name="Enabled Team",
        system_prompt="Prompt",
        enabled=True
    )
    await teams.create_team(
        name="Disabled Team",
        system_prompt="Prompt",
        enabled=False
    )

    enabled_teams = await teams.list_teams(enabled_only=True)
    assert all(t["enabled"] is True for t in enabled_teams)
    assert any(t["id"] == enabled_id for t in enabled_teams)
