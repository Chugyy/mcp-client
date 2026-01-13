#!/usr/bin/env python3
# app/core/validators/agents.py
"""Validateurs pour les agents."""

from typing import List, Optional
from app.core.validators.base import BaseValidator
from app.core.exceptions import ConflictError, QuotaExceededError, ValidationError


class AgentValidator(BaseValidator):
    """Validateurs spécifiques aux agents."""

    @staticmethod
    async def validate_name_unique(name: str, user_id: str, exclude_id: Optional[str] = None) -> None:
        """
        Valide qu'un nom d'agent est unique pour un utilisateur.

        Args:
            name: Nom de l'agent à vérifier
            user_id: ID de l'utilisateur
            exclude_id: ID de l'agent à exclure (pour UPDATE)

        Raises:
            ConflictError: Si le nom existe déjà pour cet utilisateur
        """
        from app.database.crud.agents import get_agent_by_name_and_user

        existing = await get_agent_by_name_and_user(name, user_id)

        # Si un agent existe avec ce nom
        if existing:
            # Si exclude_id est fourni (mode UPDATE), vérifier que ce n'est pas le même agent
            if exclude_id and existing['id'] == exclude_id:
                return  # C'est le même agent, OK

            # Sinon, c'est un doublon
            raise ConflictError(f"Agent name '{name}' already exists for this user")

    @staticmethod
    async def validate_agent_quota(user_id: str, is_admin: bool = False) -> None:
        """
        Valide que l'utilisateur n'a pas dépassé son quota d'agents.

        Quota: 100 agents max par user (sauf admin = illimité)

        Args:
            user_id: ID de l'utilisateur
            is_admin: Si True, pas de limite

        Raises:
            QuotaExceededError: Si le quota est dépassé
        """
        # Admin = quota illimité
        if is_admin:
            return

        from app.database.crud.agents import count_agents_by_user

        count = await count_agents_by_user(user_id)

        if count >= 100:
            raise QuotaExceededError(
                f"Agent quota exceeded. Maximum 100 agents allowed per user, you have {count}."
            )

    @staticmethod
    def validate_tags(tags: List[str]) -> List[str]:
        """
        Valide et normalise les tags.

        Args:
            tags: Liste de tags à valider

        Returns:
            Liste de tags normalisés

        Raises:
            ValidationError: Si validation échoue
        """
        if not tags:
            return []

        if len(tags) > 50:
            raise ValidationError('Too many tags (max 50)')

        normalized = []
        for tag in tags:
            if not isinstance(tag, str):
                continue

            cleaned = tag.strip().lower()

            if not cleaned:
                continue

            if len(cleaned) > 50:
                raise ValidationError(f'Tag too long: "{cleaned}" (max 50 characters)')

            if cleaned not in normalized:
                normalized.append(cleaned)

        return normalized

    @staticmethod
    def validate_system_prompt(system_prompt: str) -> str:
        """
        Valide le system prompt.

        Args:
            system_prompt: System prompt à valider

        Returns:
            System prompt validé (trimmed)

        Raises:
            ValidationError: Si validation échoue
        """
        if not system_prompt or not system_prompt.strip():
            raise ValidationError('system_prompt cannot be empty')

        cleaned = system_prompt.strip()

        if len(cleaned) > 10000:
            raise ValidationError('system_prompt too long (max 10000 characters)')

        return cleaned
