from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from app.database import crud
from app.core.services.mcp.oauth_manager import OAuthManager
from config.logger import logger
from config.config import settings
from app.core.exceptions import ValidationError, NotFoundError

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection")
):
    """
    Callback OAuth 2.1 - Reçoit le code d'autorisation et l'échange contre un token.

    Workflow :
    1. Récupérer la session OAuth par state
    2. Récupérer le serveur MCP et ses metadata
    3. Échanger le code contre un access token
    4. Stocker les tokens en BDD
    5. Récupérer les tools du serveur MCP
    6. Mettre à jour le status du serveur à 'active'
    7. Rediriger vers le frontend
    """
    logger.info(f"OAuth callback received with state: {state}")

    # 1. Récupérer la session OAuth
    session = await OAuthManager.get_session(state)
    if not session:
        logger.error(f"No OAuth session found for state: {state}")
        raise ValidationError("Invalid or expired OAuth session")

    server_id = session['server_id']
    code_verifier = session['code_verifier']
    redirect_uri = session['redirect_uri']

    # 2. Récupérer le serveur MCP
    server_data = await crud.get_server(server_id)
    if not server_data:
        logger.error(f"Server {server_id} not found")
        raise NotFoundError("Server not found")

    server_url = server_data['url']

    # 3. Redécouvrir les metadata OAuth (pour obtenir le token_endpoint)
    discovery = await OAuthManager.discover_metadata(server_url)
    if not discovery['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"OAuth metadata rediscovery failed: {discovery['error']}"
        )
        raise ValidationError(f"OAuth discovery failed: {discovery['error']}")

    prm = await OAuthManager.fetch_protected_resource(discovery['resource_metadata_url'])
    if not prm['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"Failed to fetch protected resource metadata: {prm['error']}"
        )
        raise ValidationError(f"Protected resource metadata error: {prm['error']}")

    auth_server_url = prm['authorization_servers'][0]
    asm = await OAuthManager.fetch_authorization_server(auth_server_url)
    if not asm['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"Failed to fetch authorization server metadata: {asm['error']}"
        )
        raise ValidationError(f"Authorization server metadata error: {asm['error']}")

    # 4. Échanger le code contre un access token
    client_id = settings.oauth_client_id
    token_result = await OAuthManager.exchange_code(
        token_endpoint=asm['token_endpoint'],
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        client_id=client_id
    )

    if not token_result['success']:
        await crud.update_server_status(
            server_id=server_id,
            status='failed',
            status_message=f"Token exchange failed: {token_result['error']}"
        )
        raise ValidationError(f"Token exchange failed: {token_result['error']}")

    # 5. Stocker les tokens en BDD
    await OAuthManager.store_tokens(
        server_id=server_id,
        access_token=token_result['access_token'],
        refresh_token=token_result['refresh_token'],
        expires_in=token_result['expires_in'],
        token_type=token_result['token_type'],
        scope=token_result['scope']
    )

    logger.info(f"Successfully stored OAuth tokens for server {server_id}")

    # 6. Vérifier le serveur et récupérer les tools
    from app.core.services.mcp.manager import ServerManager
    await ServerManager.verify(server_id)

    # 7. Nettoyer la session OAuth
    await OAuthManager.delete_session(session['id'])

    # 10. Rediriger vers le frontend
    frontend_url = settings.frontend_url
    return RedirectResponse(url=f"{frontend_url}/servers/{server_id}?oauth_success=true")
