from fastapi import APIRouter, Depends, status
from typing import List
from app.database import crud
from app.database.models import User, Team, Agent
from app.api.v1.schemas import (
    TeamCreate, TeamUpdate, TeamResponse,
    MembershipCreate, MembershipResponse, AgentResponse
)
from app.core.utils.auth import get_current_user
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException

router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: TeamCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle équipe."""
    team_id = await crud.create_team(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        tags=request.tags,
        enabled=request.enabled
    )

    team = await crud.get_team(team_id)
    if not team:
        raise AppException("Failed to create team")

    team = Team.from_row(team)
    return TeamResponse(**team.to_dict())

@router.get("", response_model=List[TeamResponse])
async def list_teams(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Liste toutes les équipes."""
    team_rows = await crud.list_teams(enabled_only=enabled_only)
    return [TeamResponse(**Team.from_row(t).to_dict()) for t in team_rows]

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: str, current_user: User = Depends(get_current_user)):
    """Récupère une équipe par ID."""
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    team = Team.from_row(team)
    return TeamResponse(**team.to_dict())

@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    request: TeamUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour une équipe."""
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    success = await crud.update_team(
        team_id=team_id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        tags=request.tags,
        enabled=request.enabled
    )

    if not success:
        raise AppException("Failed to update team")

    team = await crud.get_team(team_id)
    team = Team.from_row(team)

    return TeamResponse(**team.to_dict())

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: str, current_user: User = Depends(get_current_user)):
    """Supprime une équipe."""
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    success = await crud.delete_team(team_id)
    if not success:
        raise AppException("Failed to delete team")

    return None

@router.post("/{team_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    team_id: str,
    request: MembershipCreate,
    current_user: User = Depends(get_current_user)
):
    """Ajoute un agent à l'équipe."""
    # Vérifier que l'équipe existe
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = await crud.get_agent(request.agent_id)
    if not agent:
        raise NotFoundError("Agent not found")

    agent = Agent.from_row(agent)
    if agent.user_id != current_user.id:
        raise PermissionError("Not authorized to add this agent")

    # Ajouter l'agent à l'équipe
    try:
        membership_id = await crud.add_member(
            team_id=team_id,
            agent_id=request.agent_id,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(f"Failed to add member: {str(e)}")

    # Récupérer le membership créé depuis la DB
    from app.database.models import Membership
    membership = await crud.get_membership(membership_id)
    if not membership:
        raise AppException("Failed to retrieve created membership")

    membership = Membership.from_row(membership)
    return MembershipResponse(**membership.to_dict())

@router.get("/{team_id}/members", response_model=List[AgentResponse])
async def list_members(
    team_id: str,
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Liste les membres (agents) d'une équipe."""
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    members = await crud.list_team_members(team_id, enabled_only=enabled_only)
    return [AgentResponse(**Agent.from_row(m).to_dict()) for m in members]

@router.delete("/{team_id}/members/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    team_id: str,
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retire un agent de l'équipe."""
    # Vérifier que l'équipe existe
    team = await crud.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")

    # Vérifier que l'agent appartient à l'utilisateur
    agent = await crud.get_agent(agent_id)
    if agent:
        agent = Agent.from_row(agent)
        if agent.user_id != current_user.id:
            raise PermissionError("Not authorized")

    success = await crud.remove_member(team_id, agent_id)
    if not success:
        raise NotFoundError("Membership not found")

    return None
