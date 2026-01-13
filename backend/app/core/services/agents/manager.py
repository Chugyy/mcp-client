#!/usr/bin/env python3
# app/core/services/agents/manager.py
"""Service layer pour la gestion des agents."""

from typing import Optional
from app.core.services.base import BaseService
from app.core.validators.agents import AgentValidator
from app.core.exceptions import NotFoundError, PermissionError
from app.database import crud


class AgentManager(BaseService):
    """Gestionnaire des agents avec règles métier."""

    @staticmethod
    async def create(dto, user_id: str, avatar=None) -> str:
        """
        Crée un agent avec toutes les validations.

        Args:
            dto: AgentCreate schema
            user_id: ID de l'utilisateur
            avatar: Fichier avatar (optionnel)

        Returns:
            ID de l'agent créé

        Raises:
            QuotaExceededError: Si quota dépassé
            ConflictError: Si nom déjà utilisé
            ValidationError: Si données invalides
        """
        # 1. Vérifier quota
        await AgentValidator.validate_agent_quota(user_id)

        # 2. Vérifier unicité nom
        await AgentValidator.validate_name_unique(dto.name, user_id)

        # 3. Créer agent
        agent_id = await crud.create_agent(
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            system_prompt=dto.system_prompt,
            tags=dto.tags,
            enabled=dto.enabled
        )

        # 4. Upload avatar si fourni
        if avatar:
            from app.database.crud import uploads
            await uploads.save_upload(agent_id, avatar, 'avatar')

        # 5. Créer configurations MCP
        if dto.mcp_configs:
            from app.database.crud import servers
            for mcp in dto.mcp_configs:
                server_id = mcp.get('server_id')
                mcp_enabled = mcp.get('enabled', True)
                tools = mcp.get('tools', [])

                if server_id:
                    await servers.create_configuration(
                        agent_id=agent_id,
                        entity_type='server',
                        entity_id=server_id,
                        config_data={'tools': tools},
                        enabled=mcp_enabled
                    )

        # 6. Créer configurations resources
        if dto.resources:
            from app.database.crud import servers
            for res in dto.resources:
                resource_id = res.get('id')
                resource_enabled = res.get('enabled', True)

                if resource_id:
                    await servers.create_configuration(
                        agent_id=agent_id,
                        entity_type='resource',
                        entity_id=resource_id,
                        config_data={},
                        enabled=resource_enabled
                    )

        return agent_id

    @staticmethod
    async def update(agent_id: str, dto, user_id: str, avatar=None) -> bool:
        """
        Met à jour un agent avec validations.

        Args:
            agent_id: ID de l'agent
            dto: AgentUpdate schema
            user_id: ID de l'utilisateur
            avatar: Fichier avatar (optionnel)

        Returns:
            True si succès

        Raises:
            NotFoundError: Si agent inexistant
            PermissionError: Si pas propriétaire ou agent système
            ConflictError: Si nom déjà utilisé
        """
        # 1. Vérifier existence
        agent = await crud.get_agent(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")

        from app.database.models import Agent
        agent_obj = Agent.from_row(agent)

        # 2. Vérifier protection système
        if agent_obj.is_system:
            raise PermissionError(
                "Cannot modify system agent. System agents are read-only."
            )

        # 3. Vérifier ownership
        if agent_obj.user_id != user_id:
            raise PermissionError("Not authorized to update this agent")

        # 4. Vérifier unicité nom (si changement)
        if dto.name and dto.name != agent_obj.name:
            await AgentValidator.validate_name_unique(dto.name, user_id, agent_id)

        # 5. Mettre à jour
        success = await crud.update_agent(
            agent_id=agent_id,
            name=dto.name,
            description=dto.description,
            system_prompt=dto.system_prompt,
            tags=dto.tags,
            enabled=dto.enabled
        )

        if not success:
            raise NotFoundError("Failed to update agent")

        # 6. Update avatar si fourni
        if avatar:
            from app.database.crud import uploads
            await uploads.delete_agent_avatar(agent_id)
            await uploads.save_upload(agent_id, avatar, 'avatar')

        # 7. Update MCP configurations si fourni
        if dto.mcp_configs is not None:
            from app.database.crud import servers

            # Delete existing server configurations
            existing_configs = await servers.list_configurations_by_agent(agent_id, 'server')
            for config in existing_configs:
                await servers.delete_configuration(config['id'])

            # Create new configurations
            for mcp in dto.mcp_configs:
                server_id = mcp.get('server_id')
                mcp_enabled = mcp.get('enabled', True)
                tools = mcp.get('tools', [])

                if server_id:
                    await servers.create_configuration(
                        agent_id=agent_id,
                        entity_type='server',
                        entity_id=server_id,
                        config_data={'tools': tools},
                        enabled=mcp_enabled
                    )

        # 8. Update resource configurations si fourni
        if dto.resources is not None:
            from app.database.crud import servers

            # Delete existing resource configurations
            existing_configs = await servers.list_configurations_by_agent(agent_id, 'resource')
            for config in existing_configs:
                await servers.delete_configuration(config['id'])

            # Create new configurations
            for res in dto.resources:
                resource_id = res.get('id')
                resource_enabled = res.get('enabled', True)

                if resource_id:
                    await servers.create_configuration(
                        agent_id=agent_id,
                        entity_type='resource',
                        entity_id=resource_id,
                        config_data={},
                        enabled=resource_enabled
                    )

        return True

    @staticmethod
    async def delete(agent_id: str, user_id: str, force: bool = False) -> bool:
        """
        Supprime un agent avec vérifications.

        Args:
            agent_id: ID de l'agent
            user_id: ID de l'utilisateur
            force: Si True, supprime même avec impact

        Returns:
            True si succès

        Raises:
            NotFoundError: Si agent inexistant
            PermissionError: Si pas propriétaire ou agent système
            RuntimeError: Si impact détecté ET force=False (409)
        """
        # 1. Vérifier existence
        agent = await crud.get_agent(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")

        from app.database.models import Agent
        agent_obj = Agent.from_row(agent)

        # 2. Vérifier protection système
        if agent_obj.is_system:
            raise PermissionError(
                "Cannot delete system agent. System agents are protected and cannot be removed."
            )

        # 3. Vérifier ownership
        if agent_obj.user_id != user_id:
            raise PermissionError("Not authorized to delete this agent")

        # 4. Calculer impact
        from app.database.crud import chats as crud_chats
        chat_count = await crud_chats.count_chats_by_agent(agent_id)

        # 5. Si impact détecté ET pas de confirmation → RuntimeError (409)
        if chat_count > 0 and not force:
            raise RuntimeError(f"Agent has {chat_count} chats. Use force=True to delete anyway.")

        # 6. Suppression (CASCADE géré par la BDD)
        success = await crud.delete_agent(agent_id)
        if not success:
            raise NotFoundError("Failed to delete agent")

        return True
