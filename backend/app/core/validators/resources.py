#!/usr/bin/env python3
# app/core/validators/resources.py
"""
Validateurs métier pour les ressources RAG.
Conformes au pattern MCP.
"""

from typing import Optional
from app.core.validators.base import BaseValidator
from app.core.exceptions import ConflictError, QuotaExceededError, ValidationError


class ResourceValidator(BaseValidator):
    """Validateurs pour les ressources RAG."""

    # Quota par défaut (ressources/utilisateur)
    DEFAULT_QUOTA = 50
    ADMIN_QUOTA = 100

    # Modèles d'embedding autorisés
    ALLOWED_EMBEDDING_MODELS = [
        'text-embedding-3-small',
        'text-embedding-3-large',
        'text-embedding-ada-002'
    ]

    @staticmethod
    async def validate_name_unique(
        name: str,
        user_id: str,
        exclude_id: Optional[str] = None
    ) -> None:
        """
        Vérifie qu'aucune autre ressource du même utilisateur n'a ce nom.

        Args:
            name: Nom de la ressource
            user_id: ID de l'utilisateur
            exclude_id: ID à exclure (pour update)

        Raises:
            ConflictError: Si nom déjà utilisé par cet utilisateur
        """
        from app.database.crud.resources import get_resource_by_name_and_user

        existing = await get_resource_by_name_and_user(name, user_id)

        # Si ressource trouvée et ce n'est pas celle qu'on exclut
        if existing and existing.get('id') != exclude_id:
            raise ConflictError(
                f"Resource named '{name}' already exists for this user",
                details={'name': name, 'user_id': user_id}
            )

    @staticmethod
    async def validate_resource_quota(
        user_id: str,
        is_admin: bool = False
    ) -> None:
        """
        Vérifie que l'utilisateur n'a pas dépassé son quota de ressources.

        Args:
            user_id: ID de l'utilisateur
            is_admin: Si True, quota augmenté (illimité pour super-admin)

        Raises:
            QuotaExceededError: Si quota dépassé
        """
        from app.database.crud.resources import count_resources_by_user

        # Admin = quota illimité (géré par BaseService.check_quota)
        if is_admin:
            return

        count = await count_resources_by_user(user_id)
        limit = ResourceValidator.DEFAULT_QUOTA

        if count >= limit:
            raise QuotaExceededError(
                f"Resource quota exceeded. Maximum {limit} resources allowed, you have {count}.",
                details={'current': count, 'limit': limit}
            )

    @staticmethod
    def validate_embedding_config(model: str, dimension: int) -> None:
        """
        Vérifie que la dimension correspond au modèle d'embedding.

        Args:
            model: Nom du modèle
            dimension: Dimension attendue

        Raises:
            ValidationError: Si incompatibilité détectée
        """
        expected_dims = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536
        }

        if model not in ResourceValidator.ALLOWED_EMBEDDING_MODELS:
            raise ValidationError(
                f"Invalid embedding model '{model}'. "
                f"Allowed: {', '.join(ResourceValidator.ALLOWED_EMBEDDING_MODELS)}"
            )

        expected = expected_dims.get(model)
        if expected and dimension != expected:
            raise ValidationError(
                f"Model '{model}' expects dimension {expected}, got {dimension}"
            )
