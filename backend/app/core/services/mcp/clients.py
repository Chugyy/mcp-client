#!/usr/bin/env python3
# app/core/services/mcp/executor.py

import httpx
import json
from typing import Dict, Optional, Any
from config.logger import logger
from app.database.crud.servers import get_server
from app.database.crud.api_keys import get_api_key_decrypted
from .base import MCPClient

TIMEOUT = 30.0


# ============================================================================
# HTTP CLIENT
# ============================================================================

class HTTPMCPClient(MCPClient):
    """Client MCP pour serveurs HTTP avec support OAuth et API Key."""

    def __init__(self, server_id: str, url: str, auth_type: str,
                 api_key: Optional[str] = None, api_key_id: Optional[str] = None,
                 user_id: Optional[str] = None, is_system: bool = False):
        self.server_id = server_id
        self.url = url.rstrip('/')
        self.auth_type = auth_type
        self.api_key = api_key
        self.api_key_id = api_key_id
        self.user_id = user_id
        self.is_system = is_system

    async def _get_access_token(self) -> Optional[str]:
        """Récupère et rafraîchit l'access token si nécessaire (OAuth ou API Key)."""
        if self.auth_type == 'oauth':
            from app.core.services.mcp import token, oauth
            from config.config import settings

            # Récupérer les tokens OAuth
            tokens = await token.get_oauth_tokens(self.server_id)
            if not tokens:
                logger.error(f"No OAuth tokens found for server {self.server_id}")
                return None

            # Vérifier si le token est expiré
            if await token.is_token_expired(self.server_id):
                logger.info(f"Access token expired for server {self.server_id}, refreshing...")

                # Redécouvrir les metadata pour obtenir le token_endpoint
                discovery = await oauth.discover_oauth_metadata_from_401(self.url)
                if not discovery['success']:
                    logger.error(f"OAuth metadata rediscovery failed: {discovery['error']}")
                    return None

                prm = await oauth.fetch_protected_resource_metadata(discovery['resource_metadata_url'])
                if not prm['success']:
                    logger.error(f"Protected resource metadata error: {prm['error']}")
                    return None

                auth_server_url = prm['authorization_servers'][0]
                asm = await oauth.fetch_authorization_server_metadata(auth_server_url)
                if not asm['success']:
                    logger.error(f"Authorization server metadata error: {asm['error']}")
                    return None

                # Rafraîchir le token
                refresh_result = await oauth.refresh_access_token(
                    token_endpoint=asm['token_endpoint'],
                    client_id=settings.oauth_client_id,
                    refresh_token=tokens['refresh_token']
                )

                if not refresh_result['success']:
                    logger.error(f"Token refresh failed for server {self.server_id}")
                    return None

                # Mettre à jour les tokens en BDD
                await token.update_oauth_tokens(
                    server_id=self.server_id,
                    access_token=refresh_result['access_token'],
                    refresh_token=refresh_result['refresh_token'],
                    expires_in=refresh_result['expires_in']
                )

                logger.info(f"Successfully refreshed access token for server {self.server_id}")
                return refresh_result['access_token']
            else:
                # Token valide
                return tokens['access_token']

        elif self.auth_type == 'api-key' and self.api_key_id:
            api_key = await get_api_key_decrypted(self.api_key_id)
            if not api_key:
                logger.error(f"API key not found for server {self.server_id}")
                return None
            return api_key

        return self.api_key

    def _get_headers(self, access_token: Optional[str] = None) -> dict:
        """Construit les headers HTTP."""
        headers = {"Content-Type": "application/json"}

        if self.auth_type in ['api-key', 'oauth'] and access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        if self.is_system and self.user_id:
            headers["X-Internal-User-ID"] = self.user_id
            logger.info(f"🔐 [HTTPMCPClient] Serveur interne, ajout header X-Internal-User-ID: {self.user_id}")
        elif self.is_system:
            logger.warning(f"⚠️  [HTTPMCPClient] Serveur interne mais user_id non fourni")

        return headers

    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Appelle un outil via HTTP/JSON-RPC."""
        # Récupérer l'access token
        access_token = await self._get_access_token()
        if self.auth_type in ['api-key', 'oauth'] and not access_token:
            return {
                "success": False,
                "result": None,
                "error": "Authentication failed: unable to get access token"
            }

        mcp_url = f"{self.url}/mcp/"
        headers = self._get_headers(access_token)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        logger.info(f"📤 [HTTPMCPClient] Appel MCP - Server: {self.server_id}, Tool: {tool_name}, User ID: {self.user_id}")
        logger.debug(f"📦 [HTTPMCPClient] Headers: {headers}")

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            try:
                logger.debug(f"Calling HTTP tool '{tool_name}' on {mcp_url}")
                logger.debug(f"MCP payload: {payload}")
                response = await client.post(mcp_url, json=payload, headers=headers)

                if response.status_code != 200:
                    logger.error(f"Tool call failed with HTTP {response.status_code}")
                    return {
                        "success": False,
                        "result": None,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

                data = response.json()

                # Vérifier la réponse JSON-RPC
                if data.get("error"):
                    error_msg = data["error"].get("message", "Unknown error")
                    logger.error(f"Tool execution error: {error_msg}")
                    return {
                        "success": False,
                        "result": None,
                        "error": error_msg
                    }
                elif "result" in data:
                    logger.debug(f"Tool '{tool_name}' executed successfully")
                    return {
                        "success": True,
                        "result": data["result"],
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "result": None,
                        "error": "Invalid JSON-RPC response structure"
                    }

            except httpx.TimeoutException:
                logger.error(f"Timeout calling tool '{tool_name}'")
                return {
                    "success": False,
                    "result": None,
                    "error": f"Timeout after {TIMEOUT}s"
                }
            except Exception as e:
                logger.error(f"Error calling HTTP tool: {e}")
                return {
                    "success": False,
                    "result": None,
                    "error": str(e)
                }

    async def list_tools(self) -> Dict[str, Any]:
        """Liste les outils via HTTP/JSON-RPC."""
        # Récupérer l'access token
        access_token = await self._get_access_token()
        if self.auth_type in ['api-key', 'oauth'] and not access_token:
            return {
                "success": False,
                "tools": [],
                "count": 0,
                "error": "Authentication failed: unable to get access token"
            }

        mcp_url = f"{self.url}/mcp/"
        headers = self._get_headers(access_token)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            try:
                response = await client.post(mcp_url, json=payload, headers=headers)

                if response.status_code != 200:
                    return {
                        "success": False,
                        "tools": [],
                        "count": 0,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

                data = response.json()

                if data.get("error"):
                    return {
                        "success": False,
                        "tools": [],
                        "count": 0,
                        "error": data["error"].get("message", "Unknown error")
                    }
                elif "result" in data:
                    tools = data["result"].get("tools", [])
                    return {
                        "success": True,
                        "tools": tools,
                        "count": len(tools),
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "tools": [],
                        "count": 0,
                        "error": "Invalid JSON-RPC response structure"
                    }

            except httpx.TimeoutException:
                return {
                    "success": False,
                    "tools": [],
                    "count": 0,
                    "error": f"Timeout after {TIMEOUT}s"
                }
            except Exception as e:
                return {
                    "success": False,
                    "tools": [],
                    "count": 0,
                    "error": str(e)
                }

    async def verify(self) -> Dict[str, Any]:
        """Vérifie le serveur HTTP."""
        # Appeler list_tools pour vérifier la connexion
        tools_result = await self.list_tools()

        if tools_result["success"]:
            return {
                "status": "active",
                "status_message": f"Server active with {tools_result['count']} tool(s)",
                "tools": tools_result["tools"]
            }
        else:
            # Déterminer le type d'erreur
            error = tools_result.get("error", "Unknown error")
            if "Authentication failed" in error or "401" in error:
                status = "failed"
                status_message = f"Authentication error: {error}"
            elif "Timeout" in error or "unreachable" in error.lower():
                status = "unreachable"
                status_message = f"Server unreachable: {error}"
            else:
                status = "failed"
                status_message = f"Verification failed: {error}"

            return {
                "status": status,
                "status_message": status_message,
                "tools": []
            }


# ============================================================================
# STDIO CLIENT
# ============================================================================

class StdioMCPClient(MCPClient):
    """Client MCP pour serveurs stdio (locaux) avec sessions éphémères."""

    def __init__(self, command: str, args: list, env: dict):
        self.command = command
        self.args = args
        self.env = env

    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """
        Appelle un outil via stdio.
        Session éphémère : lance → call_tool → ferme
        """
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env
            )

            logger.debug(f"🚀 [StdioMCPClient] Launching stdio server: {self.command} {self.args}")

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()

                    # Call tool
                    logger.debug(f"📞 [StdioMCPClient] Calling stdio tool '{tool_name}'")
                    result = await session.call_tool(tool_name, arguments)

                    # Convertir CallToolResult en dict sérialisable
                    result_dict = {
                        "content": [
                            {
                                "type": item.type,
                                "text": item.text if hasattr(item, 'text') else None
                            }
                            for item in result.content
                        ] if hasattr(result, 'content') else [],
                        "isError": result.isError if hasattr(result, 'isError') else False
                    }

                    logger.debug(f"✅ [StdioMCPClient] Tool '{tool_name}' executed successfully")
                    return {
                        "success": True,
                        "result": result_dict,
                        "error": None
                    }

        except Exception as e:
            logger.error(f"❌ [StdioMCPClient] Error calling stdio tool: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    async def list_tools(self) -> Dict[str, Any]:
        """
        Liste les outils via stdio.
        Session éphémère : lance → list_tools → ferme
        """
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env
            )

            logger.debug(f"🚀 [StdioMCPClient] Launching stdio server for list_tools: {self.command}")

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()

                    # List tools
                    result = await session.list_tools()

                    tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in result.tools
                    ]

                    logger.debug(f"✅ [StdioMCPClient] Found {len(tools)} tools")
                    return {
                        "success": True,
                        "tools": tools,
                        "count": len(tools),
                        "error": None
                    }

        except Exception as e:
            logger.error(f"❌ [StdioMCPClient] Error listing stdio tools: {e}")
            return {
                "success": False,
                "tools": [],
                "count": 0,
                "error": str(e)
            }

    async def verify(self) -> Dict[str, Any]:
        """Vérifie le serveur stdio en tentant de lister les outils."""
        logger.info(f"🔍 [StdioMCPClient] Verifying stdio server: {self.command} {self.args}")

        tools_result = await self.list_tools()

        if tools_result["success"]:
            return {
                "status": "active",
                "status_message": f"Server active with {tools_result['count']} tool(s)",
                "tools": tools_result["tools"]
            }
        else:
            return {
                "status": "failed",
                "status_message": f"Failed to connect: {tools_result['error']}",
                "tools": []
            }


# ============================================================================
# DOCKER CLIENT
# ============================================================================

class DockerMCPClient(MCPClient):
    """Client MCP pour serveurs Docker (stdio via container)."""

    def __init__(self, image: str, args: list, env: dict):
        """
        Args:
            image: Image Docker (ex: "ghcr.io/github/github-mcp-server")
            args: Arguments supplémentaires pour docker run (volumes, etc.)
            env: Variables d'environnement
        """
        self.image = image
        self.args = args or []
        self.env = env or {}

    def _build_docker_command(self) -> tuple[str, list]:
        """
        Construit la commande docker run complète.

        Returns:
            (command, full_args)
        """
        docker_args = [
            "run",
            "--rm",      # Auto-supprimer après exécution
            "-i",        # Maintenir stdin ouvert pour JSON-RPC
        ]

        # Ajouter variables d'environnement
        for key, value in self.env.items():
            docker_args.extend(["-e", f"{key}={value}"])

        # Ajouter args custom (volumes, network, etc.)
        docker_args.extend(self.args)

        # Image en dernier
        docker_args.append(self.image)

        return "docker", docker_args

    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Appelle un outil via Docker stdio."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            command, docker_args = self._build_docker_command()

            server_params = StdioServerParameters(
                command=command,
                args=docker_args,
                env={}  # Déjà passé dans docker_args
            )

            logger.debug(f"🐳 [DockerMCPClient] Launching container: {command} {' '.join(docker_args)}")

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()

                    # Call tool
                    logger.debug(f"🐳 [DockerMCPClient] Calling tool '{tool_name}'")
                    result = await session.call_tool(tool_name, arguments)

                    # Convertir CallToolResult en dict sérialisable
                    result_dict = {
                        "content": [
                            {
                                "type": item.type,
                                "text": item.text if hasattr(item, 'text') else None
                            }
                            for item in result.content
                        ] if hasattr(result, 'content') else [],
                        "isError": result.isError if hasattr(result, 'isError') else False
                    }

                    return {
                        "success": True,
                        "result": result_dict,
                        "error": None
                    }

        except Exception as e:
            logger.error(f"❌ [DockerMCPClient] Error calling Docker tool: {e}")

            # Détecter image manquante
            error_str = str(e)
            if "Unable to find image" in error_str or "not found" in error_str:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Docker image '{self.image}' not found locally. Docker will pull it on first use."
                }

            return {
                "success": False,
                "result": None,
                "error": error_str
            }

    async def list_tools(self) -> Dict[str, Any]:
        """Liste les outils via Docker stdio."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            command, docker_args = self._build_docker_command()

            server_params = StdioServerParameters(
                command=command,
                args=docker_args,
                env={}
            )

            logger.debug(f"🐳 [DockerMCPClient] Listing tools from image: {self.image}")

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()

                    # List tools
                    result = await session.list_tools()

                    tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in result.tools
                    ]

                    logger.info(f"✅ [DockerMCPClient] Found {len(tools)} tools from Docker image")

                    return {
                        "success": True,
                        "tools": tools,
                        "count": len(tools),
                        "error": None
                    }

        except Exception as e:
            logger.error(f"❌ [DockerMCPClient] Error listing Docker tools: {e}")
            return {
                "success": False,
                "tools": [],
                "count": 0,
                "error": str(e)
            }

    async def verify(self) -> Dict[str, Any]:
        """Vérifie le serveur Docker."""
        logger.info(f"🐳 [DockerMCPClient] Verifying Docker server: {self.image}")

        tools_result = await self.list_tools()

        if tools_result["success"]:
            return {
                "status": "active",
                "status_message": f"Docker server active with {tools_result['count']} tool(s)",
                "tools": tools_result["tools"]
            }
        else:
            return {
                "status": "failed",
                "status_message": f"Failed to connect: {tools_result['error']}",
                "tools": []
            }


# ============================================================================
# FACTORY
# ============================================================================

async def create_mcp_client(server_id: str, user_id: Optional[str] = None) -> MCPClient:
    """
    Factory qui instancie le bon client selon le type de serveur.

    Args:
        server_id: ID du serveur MCP
        user_id: ID de l'utilisateur (pour serveurs internes HTTP)

    Returns:
        HTTPMCPClient, StdioMCPClient ou DockerMCPClient

    Raises:
        ValueError: Si le serveur n'existe pas ou type invalide
    """
    server_data = await get_server(server_id)
    if not server_data:
        raise ValueError(f"Server {server_id} not found")

    server_type = server_data.get('type', 'http')

    # Décrypter env si présent
    env = json.loads(server_data.get('env', '{}'))
    # TODO: Implémenter décryptage
    # from app.core.utils.encryption import decrypt_value
    # env = {k: decrypt_value(v) for k, v in env.items()}

    if server_type == 'http':
        # Serveur HTTP distant
        url = server_data['url']
        auth_type = server_data['auth_type']
        api_key_id = server_data.get('api_key_id')
        is_system = server_data.get('is_system', False)

        # Récupérer l'API key si nécessaire
        api_key = None
        if auth_type == 'oauth':
            from app.core.services.mcp import token
            tokens = await token.get_oauth_tokens(server_id)
            if tokens:
                api_key = tokens['access_token']
        elif auth_type == 'api-key' and api_key_id:
            api_key = await get_api_key_decrypted(api_key_id)

        return HTTPMCPClient(
            server_id=server_id,
            url=url,
            auth_type=auth_type,
            api_key_id=api_key_id,
            user_id=user_id,
            is_system=is_system
        )

    elif server_type == 'npx':
        # Serveur Node.js via npx (auto-install)
        args = json.loads(server_data.get('args', '[]'))

        return StdioMCPClient(
            command='npx',
            args=args,
            env=env
        )

    elif server_type == 'uvx':
        # Serveur Python via uvx (auto-install)
        args = json.loads(server_data.get('args', '[]'))

        return StdioMCPClient(
            command='uvx',
            args=args,
            env=env
        )

    elif server_type == 'docker':
        # Serveur Docker (auto-pull)
        # Format args: [image, extra_docker_args...]
        args = json.loads(server_data.get('args', '[]'))

        if not args:
            raise ValueError("Docker server requires 'image' as first arg")

        image = args[0]
        extra_args = args[1:] if len(args) > 1 else []

        return DockerMCPClient(
            image=image,
            args=extra_args,
            env=env
        )

    else:
        raise ValueError(f"Unknown server type: {server_type}. Supported: http, npx, uvx, docker")


# ============================================================================
# FONCTIONS PUBLIQUES (façade)
# ============================================================================

async def execute_tool(server_id: str, tool_name: str, arguments: dict,
                       user_id: Optional[str] = None) -> dict:
    """
    Exécute un tool MCP sur un serveur donné.

    Args:
        server_id: ID du serveur MCP (ex: "srv_xxx" ou "srv_internal_private")
        tool_name: Nom du tool
        arguments: Arguments du tool
        user_id: ID de l'utilisateur (optionnel, utilisé pour les serveurs internes HTTP)

    Returns:
        {"success": bool, "result": Any, "error": Optional[str]}
    """
    try:
        client = await create_mcp_client(server_id, user_id)
        return await client.call_tool(tool_name, arguments or {})
    except ValueError as e:
        logger.error(f"Error creating MCP client: {e}")
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }


async def list_tools(server_id: str) -> Dict[str, Any]:
    """
    Récupère la liste des outils disponibles sur un serveur MCP.

    Args:
        server_id: ID du serveur MCP

    Returns:
        {
            "success": bool,
            "tools": List[dict],  # [{"name": "...", "description": "..."}]
            "count": int,
            "error": Optional[str]
        }
    """
    try:
        client = await create_mcp_client(server_id)
        return await client.list_tools()
    except ValueError as e:
        logger.error(f"Error creating MCP client: {e}")
        return {
            "success": False,
            "tools": [],
            "count": 0,
            "error": str(e)
        }


# Garder tool_call() pour rétrocompatibilité
async def tool_call(server_id: str, tool_name: str, arguments: Dict[str, Any] = None,
                    user_id: Optional[str] = None) -> Dict[str, Any]:
    """Alias de execute_tool() pour rétrocompatibilité."""
    return await execute_tool(server_id, tool_name, arguments or {}, user_id)
