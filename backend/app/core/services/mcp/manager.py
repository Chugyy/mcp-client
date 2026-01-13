#!/usr/bin/env python3
# app/core/services/mcp/manager.py

import asyncio
import shutil
from typing import Optional, Dict
from config.logger import logger
from app.database import crud
from app.database.crud import servers as crud_servers
from app.core.services.mcp.clients import create_mcp_client
from app.core.services.base import BaseService
from app.core.exceptions import ValidationError, ConflictError, NotFoundError, PermissionError
from app.api.v1.schemas.servers import ServerCreate


class ServerManager(BaseService):
    """Gestion centralisée des serveurs MCP."""

    @staticmethod
    async def create(dto: ServerCreate, user_id: str) -> str:
        """
        Crée un serveur en BDD avec validation complète.

        Args:
            dto: DTO de création du serveur
            user_id: ID de l'utilisateur

        Returns:
            server_id: ID du serveur créé

        Raises:
            ValidationError: Si validation échoue
            ConflictError: Si nom déjà utilisé
            QuotaExceededError: Si quota dépassé
        """
        from app.core.validators.mcp import ServerValidator
        from app.database.crud.api_keys import create_api_key_for_server
        import json

        # 1. Validation du type
        is_valid, message = ServerValidator.validate_type(dto.type)
        if not is_valid:
            raise ValidationError(message)

        # 2. Vérifier unicité nom (par user)
        await ServerValidator.validate_name_unique(dto.name, user_id)

        # 3. Validation de la config
        config = {
            'url': dto.url,
            'args': dto.args,
            'env': dto.env
        }
        is_valid, message = ServerValidator.validate_config(dto.type, config)
        if not is_valid:
            raise ValidationError(message)

        # 4. Vérifier quota
        await ServerValidator.validate_server_quota(user_id)

        # Créer le serveur selon le type
        if dto.type == 'http':
            # Gérer API key si nécessaire
            api_key_id = None
            service_id_to_use = dto.service_id

            if dto.auth_type == 'api-key':
                service_name = dto.service_id if dto.service_id else dto.name

                existing_service = None
                if dto.service_id:
                    existing_service = await crud.get_service(dto.service_id)

                if not existing_service:
                    existing_service = await crud.get_service_by_name_and_provider(
                        name=service_name,
                        provider='mcp'
                    )

                if not existing_service:
                    service_id_to_use = await crud.create_service(
                        name=service_name,
                        provider='mcp',
                        description=f"Auto-created service for MCP server: {dto.name}",
                        status='active'
                    )
                else:
                    service_id_to_use = existing_service['id']

                api_key_id = await create_api_key_for_server(
                    user_id=user_id,
                    service_id=service_id_to_use,
                    api_key_value=dto.api_key_value
                )

            # Créer le serveur HTTP
            server_id = await crud.create_server(
                name=dto.name,
                description=dto.description,
                url=dto.url,
                auth_type=dto.auth_type,
                service_id=service_id_to_use,
                api_key_id=api_key_id,
                enabled=dto.enabled,
                status='pending',
                user_id=user_id,
                type='http'
            )

            return server_id

        else:
            # Créer serveur stdio (npx, uvx, docker)
            server_id = await crud.create_server(
                name=dto.name,
                description=dto.description,
                type=dto.type,
                args=config['args'],  # Utiliser args expandés
                env=dto.env,
                enabled=dto.enabled,
                status='pending',
                user_id=user_id
            )

            return server_id

    @staticmethod
    async def verify(server_id: str, timeout: int = 30) -> None:
        """
        Vérifie un serveur avec timeout.

        Logique :
        - Créer client avec create_mcp_client()
        - Appeler client.verify() avec asyncio.timeout(timeout)
        - Mettre à jour status en BDD
        - Créer tools si succès
        - Gérer TimeoutError et Exception

        Args:
            server_id: ID du serveur à vérifier
            timeout: Timeout en secondes (défaut 30s)
        """
        try:
            logger.info(f"🔄 [ServerManager] Starting verification for server {server_id}")

            async with asyncio.timeout(timeout):
                # Créer le client MCP
                client = await create_mcp_client(server_id)

                # Vérifier le serveur
                result = await client.verify()

                # Mettre à jour le status
                await crud.update_server_status(
                    server_id=server_id,
                    status=result['status'],
                    status_message=result.get('status_message')
                )

                # Créer les tools si succès
                if result.get('tools'):
                    await crud.delete_server_tools(server_id)

                    for tool_data in result['tools']:
                        await crud.create_tool(
                            server_id=server_id,
                            name=tool_data.get('name'),
                            description=tool_data.get('description'),
                            input_schema=tool_data.get('inputSchema', {}),
                            enabled=True
                        )

                    logger.info(f"✅ [ServerManager] Created {len(result['tools'])} tools for server {server_id}")

                logger.info(f"✅ [ServerManager] Verification completed for server {server_id} - status: {result['status']}")

        except asyncio.TimeoutError:
            logger.error(f"❌ [ServerManager] Verification timeout for server {server_id} after {timeout}s")
            await crud.update_server_status(
                server_id=server_id,
                status='failed',
                status_message=f'Verification timeout after {timeout}s'
            )

        except Exception as e:
            logger.error(f"❌ [ServerManager] Error verifying server {server_id}: {e}")
            await crud.update_server_status(
                server_id=server_id,
                status='failed',
                status_message=str(e)
            )

    @staticmethod
    async def start_verify_async(server_id: str) -> None:
        """
        Lance verify() en arrière-plan.

        Args:
            server_id: ID du serveur à vérifier
        """
        asyncio.create_task(ServerManager.verify(server_id))
        logger.info(f"🚀 [ServerManager] Background verification task created for server {server_id}")

    @staticmethod
    async def sync_tools(server_id: str) -> None:
        """
        Re-synchronise les tools d'un serveur.

        Args:
            server_id: ID du serveur
        """
        logger.info(f"🔄 [ServerManager] Syncing tools for server {server_id}")

        # Mettre à jour le status à 'pending'
        await crud.update_server_status(
            server_id=server_id,
            status='pending',
            status_message='Sync in progress...'
        )

        # Lancer la vérification en arrière-plan
        await ServerManager.start_verify_async(server_id)

    @staticmethod
    async def delete(server_id: str, user_id: str, force: bool = False) -> None:
        """
        Supprime un serveur avec gestion cascade.

        Logique cascade :
        - Agents avec UNIQUEMENT ce serveur → supprimés (+ leurs chats en CASCADE)
        - Agents avec ce serveur + d'autres → gardés, configuration retirée

        Args:
            server_id: ID du serveur à supprimer
            user_id: ID de l'utilisateur (pour vérification ownership)
            force: Si True, supprime sans vérifier l'impact

        Raises:
            NotFoundError: Si serveur non trouvé
            PermissionError: Si serveur système ou pas propriétaire
            RuntimeError: Si impact détecté et force=False
        """
        from app.database.models import Server

        # 1. Vérifier que le serveur existe
        server = await crud.get_server(server_id)
        if not server:
            raise NotFoundError("Server not found")

        server_obj = Server.from_row(server)

        # 2. Vérifier ownership (sauf pour __internal__)
        if server_obj.user_id != user_id and server_obj.user_id != '__internal__':
            raise PermissionError("You don't have permission to delete this server")

        # 3. Protection: serveurs système ne peuvent PAS être supprimés
        if server_obj.is_system:
            raise PermissionError("Cannot delete system server. System servers are protected and cannot be removed.")

        # 4. Calculer l'impact complet
        impact = await crud_servers.get_server_deletion_impact(server_id)

        has_impact = (
            len(impact['agents_to_delete']) > 0 or
            len(impact['agents_to_update']) > 0 or
            impact['chats_to_delete'] > 0
        )

        # 5. Si impact détecté ET pas de confirmation → erreur
        if has_impact and not force:
            raise RuntimeError(f"Deletion would impact {len(impact['agents_to_delete'])} agents and {impact['chats_to_delete']} chats. Set force=True to confirm.")

        # 6. Suppression avec gestion des agents
        # 1. Supprimer les agents orphelins (ceux qui n'ont que ce serveur)
        for agent_data in impact['agents_to_delete']:
            await crud.delete_agent(agent_data['id'])
            # Les chats sont supprimés en CASCADE automatiquement

        # 2. Supprimer les configurations pour les agents à garder
        for agent_data in impact['agents_to_update']:
            configs = await crud_servers.list_configurations_by_agent(agent_data['id'], 'server')
            for config in configs:
                if config['entity_id'] == server_id:
                    await crud_servers.delete_configuration(config['id'])

        # 3. Supprimer le serveur (tools supprimés en CASCADE)
        success = await crud.delete_server(server_id)
        if not success:
            raise RuntimeError("Failed to delete server")

        logger.info(f"✅ [ServerManager] Server {server_id} deleted successfully")

    @staticmethod
    async def check_prerequisites() -> Dict[str, bool]:
        """
        Vérifie disponibilité npx, uvx, docker.

        Returns:
            Dict avec disponibilité de chaque outil
        """
        return {
            'npx': shutil.which('npx') is not None,
            'uvx': shutil.which('uvx') is not None,
            'docker': shutil.which('docker') is not None
        }
