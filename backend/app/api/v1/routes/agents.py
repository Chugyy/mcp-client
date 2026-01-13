from fastapi import APIRouter, Depends, status, File, Form, UploadFile, Header
from typing import List, Optional
import json
from app.database import crud
from app.database.models import User, Agent
from app.api.v1.schemas import AgentResponse  # Keep for backward compatibility
from app.core.utils.auth import get_current_user
from app.database.crud import uploads, servers, chats as crud_chats
from app.core.services.agents.manager import AgentManager
from app.core.exceptions import NotFoundError, PermissionError, ConflictError, AppException
from app.api.v1.schemas.agents import AgentCreate, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    name: str = Form(...),
    system_prompt: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    enabled: bool = Form(True),
    mcp_configs: Optional[str] = Form(None),
    resources: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """Crée un nouvel agent pour l'utilisateur connecté."""
    # Parse JSON fields
    tags_list = json.loads(tags) if tags else []
    mcp_list = json.loads(mcp_configs) if mcp_configs else []
    res_list = json.loads(resources) if resources else []

    # Create DTO
    dto = AgentCreate(
        name=name,
        system_prompt=system_prompt,
        description=description,
        tags=tags_list,
        enabled=enabled,
        mcp_configs=mcp_list,
        resources=res_list
    )

    # Delegate to service (exceptions handled by global handler)
    agent_id = await AgentManager.create(dto, current_user.id, avatar)

    # Return response
    agent = await crud.get_agent(agent_id)
    if not agent:
        raise NotFoundError("Failed to retrieve created agent")

    agent_obj = Agent.from_row(agent)
    return AgentResponse(**await agent_obj.to_dict())


@router.get("", response_model=List[AgentResponse])
async def list_agents(current_user: User = Depends(get_current_user)):
    """Liste tous les agents de l'utilisateur connecté."""
    agent_rows = await crud.list_agents_by_user(current_user.id)
    return [AgentResponse(**await Agent.from_row(a).to_dict()) for a in agent_rows]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, current_user: User = Depends(get_current_user)):
    """Récupère un agent par ID."""
    agent = await crud.get_agent(agent_id)
    if not agent:
        raise NotFoundError("Agent not found")

    agent_obj = Agent.from_row(agent)

    # Vérifier que l'agent appartient à l'utilisateur (sauf agents système)
    if agent_obj.user_id != current_user.id and not agent_obj.is_system:
        raise PermissionError("Not authorized to access this agent")

    return AgentResponse(**await agent_obj.to_dict())


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    name: Optional[str] = Form(None),
    system_prompt: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    enabled: Optional[bool] = Form(None),
    mcp_configs: Optional[str] = Form(None),
    resources: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """Met à jour un agent."""
    # Parse JSON fields
    tags_list = json.loads(tags) if tags else None
    mcp_list = json.loads(mcp_configs) if mcp_configs else None
    res_list = json.loads(resources) if resources else None

    # Create DTO
    dto = AgentUpdate(
        name=name,
        system_prompt=system_prompt,
        description=description,
        tags=tags_list,
        enabled=enabled,
        mcp_configs=mcp_list,
        resources=res_list
    )

    # Delegate to service (exceptions handled by global handler)
    await AgentManager.update(agent_id, dto, current_user.id, avatar)

    # Return updated agent
    agent = await crud.get_agent(agent_id)
    if not agent:
        raise NotFoundError("Agent not found after update")

    agent_obj = Agent.from_row(agent)
    return AgentResponse(**await agent_obj.to_dict())


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    x_confirm_deletion: bool = Header(False, alias="X-Confirm-Deletion"),
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un agent avec confirmation si des chats sont rattachés.

    Workflow:
    1. Premier appel sans header → Calcule l'impact et retourne 409 si impact
    2. Deuxième appel avec header X-Confirm-Deletion: true → Suppression forcée
    """
    try:
        # Delegate to service
        await AgentManager.delete(agent_id, current_user.id, force=x_confirm_deletion)
    except RuntimeError as e:
        # RuntimeError = impact détecté, besoin de confirmation (409)
        # Calculer l'impact pour le retour
        from app.database.crud import chats as crud_chats
        agent = await crud.get_agent(agent_id)
        agent_obj = Agent.from_row(agent) if agent else None
        chat_count = await crud_chats.count_chats_by_agent(agent_id)

        raise ConflictError(
            "Agent deletion requires confirmation due to existing chats",
            details={
                "type": "confirmation_required",
                "impact": {
                    "chats_to_delete": chat_count,
                    "agent_id": agent_id,
                    "agent_name": agent_obj.name if agent_obj else "Unknown"
                }
            }
        )

    # NotFoundError, PermissionError gérés par handler global
    return None


@router.post("/{agent_id}/duplicate", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_agent(agent_id: str, current_user: User = Depends(get_current_user)):
    """Duplique un agent existant."""
    # Vérifier que l'agent source existe
    source_agent = await crud.get_agent(agent_id)
    if not source_agent:
        raise NotFoundError("Agent not found")

    source_agent_obj = Agent.from_row(source_agent)

    # Vérifier les permissions (propriétaire ou agent système)
    if source_agent_obj.user_id != current_user.id and not source_agent_obj.is_system:
        raise PermissionError("Not authorized to duplicate this agent")

    # Dupliquer l'agent
    new_agent_id = await crud.duplicate_agent(agent_id, current_user.id)
    if not new_agent_id:
        raise AppException("Failed to duplicate agent")

    # Récupérer le nouvel agent créé
    new_agent = await crud.get_agent(new_agent_id)
    if not new_agent:
        raise AppException("Failed to retrieve duplicated agent")

    new_agent_obj = Agent.from_row(new_agent)
    return AgentResponse(**await new_agent_obj.to_dict())
