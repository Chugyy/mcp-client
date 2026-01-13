#!/usr/bin/env python3
# app/core/services/base.py
"""
Service de base avec helpers communs pour tous les services métier.
"""

from typing import Optional
from app.core.exceptions import PermissionError, QuotaExceededError, NotFoundError


class BaseService:
    """Classe de base pour tous les services métier."""

    @staticmethod
    async def check_ownership(entity_id: str, user_id: str, entity_type: str = "resource") -> bool:
        """
        Vérifie qu'une ressource appartient bien à un utilisateur.

        Args:
            entity_id: ID de la ressource
            user_id: ID de l'utilisateur
            entity_type: Type de ressource (pour le message d'erreur)

        Returns:
            True si l'utilisateur est propriétaire

        Raises:
            PermissionError: Si l'utilisateur n'est pas propriétaire
            NotFoundError: Si la ressource n'existe pas
        """
        from app.database import crud

        # Récupérer l'entité selon son type
        entity = None
        if entity_type == "server":
            entity = await crud.get_server(entity_id)
        elif entity_type == "agent":
            entity = await crud.get_agent(entity_id)
        elif entity_type == "resource":
            entity = await crud.get_resource(entity_id)
        # Ajouter d'autres types au besoin

        if not entity:
            raise NotFoundError(f"{entity_type.capitalize()} not found")

        if entity.get('user_id') != user_id:
            raise PermissionError(f"You don't have permission to access this {entity_type}")

        return True

    @staticmethod
    async def check_quota(user_id: str, resource_type: str, limit: int, is_admin: bool = False) -> None:
        """
        Vérifie qu'un utilisateur n'a pas dépassé son quota.

        Args:
            user_id: ID de l'utilisateur
            resource_type: Type de ressource (servers, agents, resources, etc.)
            limit: Limite du quota
            is_admin: Si True, pas de limite (bypass)

        Raises:
            QuotaExceededError: Si le quota est dépassé
        """
        # Admin = quota illimité
        if is_admin:
            return

        from app.database.crud.servers import count_servers_by_user
        from app.database import crud

        # Compter les ressources selon le type
        count = 0
        if resource_type == "servers":
            count = await count_servers_by_user(user_id)
        elif resource_type == "agents":
            count = await crud.count_agents_by_user(user_id)
        elif resource_type == "resources":
            count = await crud.count_resources_by_user(user_id)
        # Ajouter d'autres types au besoin

        if count >= limit:
            raise QuotaExceededError(
                f"Quota exceeded for {resource_type}. Maximum {limit} allowed, you have {count}."
            )
