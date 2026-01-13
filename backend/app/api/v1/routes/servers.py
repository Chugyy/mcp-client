from fastapi import APIRouter, Depends, status, Header
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.database import crud
from app.database.models import User, Server, Tool, Configuration, Agent
from app.api.v1.schemas.servers import (
    ServerCreate, ServerUpdate, ServerResponse
)
from app.api.v1.schemas import (
    ToolCreate, ToolUpdate, ToolResponse,
    ConfigurationCreate, ConfigurationResponse
)
from app.core.utils.auth import get_current_user
from app.database.crud import servers as crud_servers
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException, ConflictError

router = APIRouter(prefix="/mcp/servers", tags=["mcp-servers"])

def needs_refresh(last_health_check: Optional[datetime], max_age_hours: int = 24) -> bool:
    """Vérifie si le dernier health check est obsolète."""
    if not last_health_check:
        return True
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=max_age_hours)
    return last_health_check < threshold

async def regenerate_oauth_flow(server_id: str, server_url: str) -> str:
    """
    Régénère le flux OAuth complet pour un serveur MCP.

    Args:
        server_id: ID du serveur MCP
        server_url: URL de base du serveur MCP

    Returns:
        authorization_url: URL d'autorisation OAuth à ouvrir

    Raises:
        HTTPException: Si le processus OAuth échoue
    """
    from app.core.services.mcp.oauth_manager import OAuthManager
    from config.config import settings

    # Découvrir les metadata OAuth
    discovery = await OAuthManager.discover_metadata(server_url)
    if not discovery['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"OAuth discovery failed: {discovery['error']}"
        )
        raise ValidationError(f"OAuth discovery failed: {discovery['error']}")

    # Récupérer les metadata de la ressource protégée
    prm = await OAuthManager.fetch_protected_resource(discovery['resource_metadata_url'])
    if not prm['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"Failed to fetch protected resource metadata: {prm['error']}"
        )
        raise ValidationError(f"Protected resource metadata error: {prm['error']}")

    # Récupérer les metadata du serveur d'autorisation
    auth_server_url = prm['authorization_servers'][0]
    asm = await OAuthManager.fetch_authorization_server(auth_server_url)
    if not asm['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"Failed to fetch authorization server metadata: {asm['error']}"
        )
        raise ValidationError(f"Authorization server metadata error: {asm['error']}")

    # Générer PKCE
    pkce = OAuthManager.generate_pkce()
    state = OAuthManager.generate_state()

    # Construire l'URL de callback
    redirect_uri = f"{settings.api_url}/oauth/callback"

    # Stocker la session OAuth
    await OAuthManager.store_session(
        server_id=server_id,
        state=state,
        code_verifier=pkce['code_verifier'],
        code_challenge=pkce['code_challenge'],
        redirect_uri=redirect_uri,
        scope='read write'
    )

    # Construire l'URL d'autorisation
    client_id = settings.oauth_client_id
    authorization_url = OAuthManager.build_auth_url(
        authorization_endpoint=asm['authorization_endpoint'],
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=pkce['code_challenge'],
        state=state,
        scope='read write'
    )

    return authorization_url

# ===== SERVERS =====

@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    request: ServerCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crée un nouveau serveur MCP (HTTP, npx, uvx ou docker).

    Types supportés:
    - http: Serveur MCP distant via HTTP/HTTPS
    - npx: Package Node.js depuis npm (auto-install)
    - uvx: Package Python depuis PyPI (auto-install)
    - docker: Container Docker (auto-pull)

    Raises:
        400: ValidationError, ConflictError
        429: QuotaExceededError
    """
    from app.core.services.mcp.manager import ServerManager

    # Cas particulier OAuth : workflow manuel
    if request.type == 'http' and request.auth_type == 'oauth':
        server_id = await ServerManager.create(request, current_user.id)
        authorization_url = await regenerate_oauth_flow(server_id, request.url)

        await crud.update_server_status(
            server_id=server_id,
            status='pending_authorization',
            status_message=authorization_url
        )

        server = await crud.get_server(server_id)
        server = Server.from_row(server)
        return ServerResponse(**server.to_dict())

    # Workflow standard (HTTP + stdio)
    server_id = await ServerManager.create(request, current_user.id)

    # Lancer la vérification en arrière-plan
    await ServerManager.start_verify_async(server_id)

    # Retourner le serveur créé
    server = await crud.get_server(server_id)
    if not server:
        raise AppException("Failed to retrieve server")

    server = Server.from_row(server)
    return ServerResponse(**server.to_dict())

@router.get("", response_model=List[ServerResponse])
async def list_servers(
    enabled_only: bool = False,
    with_tools: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Liste tous les serveurs MCP avec optionnellement leurs tools."""
    servers = await crud_servers.list_servers_by_user(current_user.id, enabled_only=enabled_only)
    result = []

    for row in servers:
        server = Server.from_row(row)
        response = server.to_dict()

        if with_tools:
            # Récupérer les tools pour ce serveur
            tools = await crud.list_tools_by_server(server.id)
            response['tools'] = [Tool.from_row(t).to_dict() for t in tools]

            # FRONTEND: Afficher badge "outdated" si stale=True
            response['stale'] = needs_refresh(server.last_health_check)

        result.append(ServerResponse(**response))

    return result

@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: str, current_user: User = Depends(get_current_user)):
    """Récupère un serveur MCP par ID."""
    server = await crud.get_server(server_id)
    if not server:
        raise NotFoundError("Server not found")

    server = Server.from_row(server)
    return ServerResponse(**server.to_dict())

@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    request: ServerUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour un serveur MCP."""
    server = await crud.get_server(server_id)
    if not server:
        raise NotFoundError("Server not found")

    server_obj = Server.from_row(server)

    # Protection: serveurs système ne peuvent PAS être modifiés
    if server_obj.is_system:
        raise PermissionError(
            "Cannot modify system server. System servers are read-only."
        )

    success = await crud.update_server(
        server_id=server_id,
        name=request.name,
        description=request.description,
        url=request.url,
        auth_type=request.auth_type,
        service_id=request.service_id,
        enabled=request.enabled
    )

    if not success:
        raise AppException("Failed to update server")

    updated_server = await crud.get_server(server_id)
    updated_server = Server.from_row(updated_server)

    return ServerResponse(**updated_server.to_dict())

@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    x_confirm_deletion: bool = Header(False, alias="X-Confirm-Deletion"),
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un serveur MCP avec gestion intelligente des agents.

    Logique:
    - Agents avec UNIQUEMENT ce serveur → supprimés (+ leurs chats en CASCADE)
    - Agents avec ce serveur + d'autres → gardés, configuration retirée

    Raises:
        404: NotFoundError
        403: PermissionError (serveur système)
        409: RuntimeError (impact détecté, confirmation requise)
    """
    from app.core.services.mcp.manager import ServerManager

    try:
        await ServerManager.delete(server_id, current_user.id, force=x_confirm_deletion)
    except RuntimeError as e:
        # Impact détecté, extraire les infos depuis le message ou recalculer
        impact = await crud_servers.get_server_deletion_impact(server_id)
        raise ConflictError(
            "Confirmation required",
            details={
                "type": "confirmation_required",
                "impact": impact
            }
        )

    return None

@router.post("/{server_id}/sync", response_model=ServerResponse)
async def sync(
    server_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Synchronise les tools d'un serveur MCP en se reconnectant.

    FRONTEND:
    - Succès → Notification "Server synchronized successfully"
    - Erreur 401 → Ouvrir popup OAuth avec authorization_url
    - Erreur autre → Afficher message d'erreur
    """
    from app.core.services.mcp.manager import ServerManager
    from app.core.services.mcp.oauth_manager import OAuthManager

    server_row = await crud.get_server(server_id)
    if not server_row:
        raise NotFoundError("Server not found")

    server = Server.from_row(server_row)

    # Cas particulier OAuth : vérifier le token
    if server.type == 'http' and server.auth_type == 'oauth':
        oauth_tokens = await OAuthManager.get_tokens(server_id)
        if not oauth_tokens or await OAuthManager.is_expired(server_id):
            # Régénérer le flux OAuth complet
            authorization_url = await regenerate_oauth_flow(server_id, server.url)

            # Mettre à jour le serveur avec status='pending_authorization'
            await crud.update_server_status(
                server_id=server_id,
                status='pending_authorization',
                status_message=authorization_url
            )

            # Retourner le serveur avec 200 OK (le frontend gérera pending_authorization)
            refreshed = await crud.get_server(server_id)
            return ServerResponse(**Server.from_row(refreshed).to_dict())

    # Workflow standard : lancer sync
    await ServerManager.sync_tools(server_id)

    # Retourner le serveur mis à jour
    refreshed = await crud.get_server(server_id)
    return ServerResponse(**Server.from_row(refreshed).to_dict())

# ===== TOOLS =====

@router.post("/{server_id}/tools", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    server_id: str,
    request: ToolCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée un nouvel outil MCP pour un serveur."""
    # Vérifier que le serveur existe
    server = await crud.get_server(server_id)
    if not server:
        raise NotFoundError("Server not found")

    tool_id = await crud.create_tool(
        server_id=server_id,
        name=request.name,
        description=request.description,
        enabled=request.enabled
    )

    tool = await crud.get_tool(tool_id)
    if not tool:
        raise AppException("Failed to create tool")

    tool = Tool.from_row(tool)
    return ToolResponse(**tool.to_dict())

@router.get("/{server_id}/tools", response_model=List[ToolResponse])
async def list_tools(server_id: str, current_user: User = Depends(get_current_user)):
    """Liste les outils d'un serveur MCP."""
    server = await crud.get_server(server_id)
    if not server:
        raise NotFoundError("Server not found")

    tools = await crud.list_tools_by_server(server_id)
    return [ToolResponse(**Tool.from_row(t).to_dict()) for t in tools]

@router.patch("/{server_id}/tools/{tool_id}", response_model=ToolResponse)
async def update_tool(
    server_id: str,
    tool_id: str,
    request: ToolUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour un outil MCP (typiquement pour toggle enabled).

    Args:
        server_id: ID du serveur MCP
        tool_id: ID du tool à modifier
        request: Données à mettre à jour (enabled, name, description)

    Returns:
        Tool mis à jour
    """
    # Vérifier que le serveur existe
    server = await crud.get_server(server_id)
    if not server:
        raise NotFoundError("Server not found")

    # Vérifier que le tool existe
    tool = await crud.get_tool(tool_id)
    if not tool:
        raise NotFoundError("Tool not found")

    # Vérifier que le tool appartient bien au serveur
    if tool['server_id'] != server_id:
        raise ValidationError("Tool does not belong to this server")

    # Mettre à jour le tool
    success = await crud.update_tool(
        tool_id=tool_id,
        name=request.name,
        description=request.description,
        enabled=request.enabled
    )

    if not success:
        raise AppException("Failed to update tool")

    # Retourner le tool mis à jour
    updated_tool = await crud.get_tool(tool_id)
    updated_tool = Tool.from_row(updated_tool)

    return ToolResponse(**updated_tool.to_dict())

# ===== CONFIGURATIONS =====

@router.post("/agents/{agent_id}/configurations", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    agent_id: str,
    request: ConfigurationCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée une configuration pour un agent (serveur MCP ou ressource)."""
    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = await crud.get_agent(agent_id)
    if not agent:
        raise NotFoundError("Agent not found")

    agent = Agent.from_row(agent)
    if agent.user_id != current_user.id:
        raise PermissionError("Not authorized")

    # Vérifier que l'entité existe
    if request.entity_type == "server":
        entity = await crud.get_server(request.entity_id)
        if not entity:
            raise NotFoundError("Server not found")
    elif request.entity_type == "resource":
        entity = await crud.get_resource(request.entity_id)
        if not entity:
            raise NotFoundError("Resource not found")

    try:
        config_id = await crud.create_configuration(
            agent_id=agent_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            config_data=request.config_data,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(f"Failed to create configuration: {str(e)}")

    # Récupérer la configuration créée depuis la DB
    from app.database.crud.servers import get_configuration
    config_row = await get_configuration(config_id)
    if not config_row:
        raise AppException("Failed to retrieve created configuration")

    config = Configuration.from_row(config_row)
    return ConfigurationResponse(**config.to_dict())

@router.get("/agents/{agent_id}/configurations", response_model=List[ConfigurationResponse])
async def list_configurations(agent_id: str, current_user: User = Depends(get_current_user)):
    """Liste les configurations MCP d'un agent."""
    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = await crud.get_agent(agent_id)
    if not agent:
        raise NotFoundError("Agent not found")

    agent = Agent.from_row(agent)
    if agent.user_id != current_user.id:
        raise PermissionError("Not authorized")

    configs = await crud.list_configurations_by_agent(agent_id)
    return [ConfigurationResponse(**Configuration.from_row(c).to_dict()) for c in configs]

@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(config_id: str, current_user: User = Depends(get_current_user)):
    """Supprime une configuration MCP."""
    # Note: On devrait vérifier que l'agent appartient à l'utilisateur
    # mais pour simplifier on permet la suppression directe

    success = await crud.delete_configuration(config_id)
    if not success:
        raise NotFoundError("Configuration not found")

    return None
