#!/usr/bin/env python3
# app/core/services/resources/manager.py
"""
Service layer pour les ressources RAG.
Conforme au pattern MCP (ARCHITECTURE_VALIDATION.md).
"""

from typing import Dict, Optional
from app.core.services.base import BaseService
from app.core.validators.resources import ResourceValidator
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.v1.schemas.resources import ResourceCreate, ResourceUpdate


class ResourceManager(BaseService):
    """Gestionnaire métier pour les ressources RAG."""

    @staticmethod
    async def create(dto: ResourceCreate, user_id: str) -> str:
        """
        Crée une ressource avec validations complètes.

        Workflow:
        1. Valider unicité du nom
        2. Valider quota utilisateur
        3. Valider configuration embeddings
        4. Créer en base de données

        Args:
            dto: Données de création
            user_id: ID de l'utilisateur propriétaire

        Returns:
            resource_id (str)

        Raises:
            ConflictError: Nom déjà utilisé
            QuotaExceededError: Quota dépassé
            ValidationError: Configuration invalide
        """
        from app.database.crud import resources as crud

        # Validation 1 : Unicité du nom
        await ResourceValidator.validate_name_unique(dto.name, user_id)

        # Validation 2 : Quota utilisateur
        await ResourceValidator.validate_resource_quota(user_id)

        # Validation 3 : Configuration embeddings
        ResourceValidator.validate_embedding_config(
            dto.embedding_model,
            dto.embedding_dim
        )

        # Création
        resource_id = await crud.create_resource(
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            enabled=dto.enabled,
            embedding_model=dto.embedding_model,
            embedding_dim=dto.embedding_dim
        )

        return resource_id

    @staticmethod
    async def update(
        resource_id: str,
        dto: ResourceUpdate,
        user_id: str
    ) -> bool:
        """
        Met à jour une ressource.

        Workflow:
        1. Vérifier ownership
        2. Si nom changé → vérifier unicité
        3. Mettre à jour

        Args:
            resource_id: ID de la ressource
            dto: Données de mise à jour
            user_id: ID de l'utilisateur

        Returns:
            True si succès

        Raises:
            NotFoundError: Ressource inexistante
            PermissionError: Pas propriétaire
            ConflictError: Nom déjà utilisé
        """
        from app.database.crud import resources as crud

        # Vérifier ownership
        await BaseService.check_ownership(resource_id, user_id, entity_type="resource")

        # Si nom changé, vérifier unicité
        if dto.name:
            await ResourceValidator.validate_name_unique(
                dto.name,
                user_id,
                exclude_id=resource_id
            )

        # Mise à jour
        success = await crud.update_resource(
            resource_id=resource_id,
            name=dto.name,
            description=dto.description,
            enabled=dto.enabled
        )

        return success

    @staticmethod
    async def delete(
        resource_id: str,
        user_id: str,
        force: bool = False
    ) -> None:
        """
        Supprime une ressource avec gestion cascade.

        Workflow:
        1. Vérifier ownership
        2. Si is_system=True → interdire suppression
        3. Calculer impact (agents, chats)
        4. Si impact ET pas force → lever RuntimeError (409)
        5. Supprimer agents orphelins
        6. Retirer configurations agents à garder
        7. Supprimer ressource (uploads/chunks CASCADE auto)

        Args:
            resource_id: ID de la ressource
            user_id: ID de l'utilisateur
            force: Si True, supprime malgré l'impact

        Raises:
            NotFoundError: Ressource inexistante
            PermissionError: Pas propriétaire ou ressource système
            RuntimeError: Impact détecté sans confirmation (409)
        """
        from app.database.crud import resources as crud
        from app.database import crud as crud_all

        # Vérifier ownership
        resource = await crud.get_resource(resource_id)
        if not resource:
            raise NotFoundError("Resource not found")

        if resource.get('user_id') != user_id:
            raise PermissionError("You don't have permission to delete this resource")

        # Protection ressource système
        if resource.get('is_system'):
            raise PermissionError("Cannot delete system resource")

        # Calculer impact
        impact = await crud.get_resource_deletion_impact(resource_id)

        # Si impact et pas de confirmation, lever erreur 409
        if not force:
            agents_to_delete = impact.get('agents_to_delete', [])
            agents_to_update = impact.get('agents_to_update', [])

            if agents_to_delete or agents_to_update:
                # RuntimeError sera intercepté par la route pour retourner 409
                raise RuntimeError("Confirmation required for cascade delete")

        # Suppression cascade
        # 1. Supprimer agents orphelins
        for agent_data in impact.get('agents_to_delete', []):
            await crud_all.delete_agent(agent_data['id'])

        # 2. Retirer configurations des agents à garder
        for agent_data in impact.get('agents_to_update', []):
            # Récupérer toutes les configs de cet agent
            from app.database.crud import servers as crud_servers
            configs = await crud_servers.list_configurations_by_agent(agent_data['id'])
            for config in configs:
                if config.get('entity_id') == resource_id and config.get('entity_type') == 'resource':
                    await crud_servers.delete_configuration(config['id'])

        # 3. Supprimer la ressource (uploads/chunks CASCADE auto en SQL)
        await crud.delete_resource(resource_id)

    @staticmethod
    async def get(resource_id: str, user_id: str) -> Dict:
        """
        Récupère une ressource en vérifiant ownership.

        Args:
            resource_id: ID de la ressource
            user_id: ID de l'utilisateur

        Returns:
            Resource dict

        Raises:
            NotFoundError: Ressource inexistante
            PermissionError: Pas propriétaire
        """
        from app.database.crud import resources as crud

        # Vérifier ownership (lève NotFoundError ou PermissionError)
        await BaseService.check_ownership(resource_id, user_id, entity_type="resource")

        # Récupérer la ressource
        resource = await crud.get_resource(resource_id)
        return resource
