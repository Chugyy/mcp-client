#!/usr/bin/env python3
"""
Validateurs pour les automations.
"""
from app.core.exceptions import QuotaExceededError, ConflictError


class AutomationValidator:
    """Validateurs métier pour les automations."""

    @staticmethod
    async def validate_automation_quota(user_id: str, is_admin: bool = False) -> None:
        """
        Vérifie que l'utilisateur n'a pas dépassé son quota d'automations.

        Args:
            user_id: ID de l'utilisateur
            is_admin: Si True, pas de limite

        Raises:
            QuotaExceededError: Si quota dépassé
        """
        if is_admin:
            return

        from app.database.crud import automations as crud

        # Compter automations de l'utilisateur
        automations = await crud.list_automations(user_id=user_id)
        count = len(automations)

        # Limite: 50 automations par utilisateur
        MAX_AUTOMATIONS = 50

        if count >= MAX_AUTOMATIONS:
            raise QuotaExceededError(
                f"Automation quota exceeded ({count}/{MAX_AUTOMATIONS}). "
                f"Please delete some automations before creating new ones."
            )

    @staticmethod
    async def validate_name_unique(
        name: str,
        user_id: str,
        exclude_id: str = None
    ) -> None:
        """
        Vérifie que le nom d'automation est unique pour cet utilisateur.

        Args:
            name: Nom de l'automation
            user_id: ID de l'utilisateur
            exclude_id: ID à exclure (pour updates)

        Raises:
            ConflictError: Si nom existe déjà
        """
        from app.database.crud import automations as crud

        # Récupérer automations de l'utilisateur
        automations = await crud.list_automations(user_id=user_id)

        # Vérifier si nom existe
        for auto in automations:
            if auto['name'] == name:
                # Si update, ignorer l'automation courante
                if exclude_id and auto['id'] == exclude_id:
                    continue

                raise ConflictError(
                    f"An automation with name '{name}' already exists for this user"
                )
