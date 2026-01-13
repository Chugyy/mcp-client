#!/usr/bin/env python3
"""
Service métier pour les automations.
"""
from typing import Dict, List, Optional
from app.core.services.base import BaseService
from app.core.validators.automation import AutomationValidator
from app.core.exceptions import PermissionError, NotFoundError
from app.api.v1.schemas.automation import AutomationCreate, AutomationUpdate


class AutomationManager(BaseService):
    """Service métier pour les automations."""

    @staticmethod
    async def create(dto: AutomationCreate, user_id: str, is_admin: bool = False) -> str:
        """
        Crée une automation avec validations complètes.

        Raises:
            QuotaExceededError: Si quota dépassé
            ConflictError: Si nom existe déjà
        """
        from app.database.crud import automations as crud

        # 1. Vérifier quota
        await AutomationValidator.validate_automation_quota(user_id, is_admin)

        # 2. Vérifier unicité nom
        await AutomationValidator.validate_name_unique(dto.name, user_id)

        # 3. Créer
        automation_id = await crud.create_automation(
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            is_system=False,
            enabled=dto.enabled
        )

        return automation_id

    @staticmethod
    async def update(
        automation_id: str,
        dto: AutomationUpdate,
        user_id: str
    ) -> Dict:
        """
        Met à jour une automation.

        Raises:
            NotFoundError: Si automation inexistante
            PermissionError: Si pas propriétaire
            ConflictError: Si nouveau nom existe déjà
        """
        from app.database.crud import automations as crud

        # 1. Vérifier existence et ownership
        automation = await crud.get_automation(automation_id)
        if not automation:
            raise NotFoundError("Automation not found")

        if automation['user_id'] != user_id:
            raise PermissionError("You don't have permission to update this automation")

        # 2. Si name changé, vérifier unicité
        if dto.name and dto.name != automation['name']:
            await AutomationValidator.validate_name_unique(
                dto.name,
                user_id,
                exclude_id=automation_id
            )

        # 3. Préparer updates
        updates = {}
        if dto.name is not None:
            updates["name"] = dto.name
        if dto.description is not None:
            updates["description"] = dto.description
        if dto.enabled is not None:
            updates["enabled"] = dto.enabled

        # 4. Mettre à jour
        if updates:
            await crud.update_automation(automation_id, **updates)

        return await crud.get_automation(automation_id)

    @staticmethod
    async def delete(automation_id: str, user_id: str, force: bool = False) -> None:
        """
        Supprime une automation.

        Raises:
            NotFoundError: Si automation inexistante
            PermissionError: Si pas propriétaire ou is_system
            RuntimeError: Si impact détecté et force=False
        """
        from app.database.crud import automations as crud
        from app.database.crud.executions import list_executions

        # 1. Vérifier existence et ownership
        automation = await crud.get_automation(automation_id)
        if not automation:
            raise NotFoundError("Automation not found")

        if automation['user_id'] != user_id:
            raise PermissionError("You don't have permission to delete this automation")

        # 2. Interdire suppression is_system
        if automation.get("is_system", False):
            raise PermissionError("Cannot delete system automation")

        # 3. Vérifier impact si force=False
        if not force:
            triggers = await crud.get_triggers(automation_id)
            executions = await list_executions(automation_id)

            if triggers or executions:
                # Lever RuntimeError pour déclencher 409 avec impact
                raise RuntimeError("Automation has active triggers or executions")

        # 4. Supprimer
        await crud.delete_automation(automation_id)

    @staticmethod
    async def enrich_automations(automations: List[Dict]) -> List[Dict]:
        """Enrichit automations avec stats, health, triggers."""
        from app.database.crud import automations as crud
        from app.database.crud.executions import list_executions
        from app.core.utils.automation_health import (
            check_automation_health,
            calculate_automation_stats,
            format_last_execution
        )

        enriched = []
        for auto in automations:
            automation_id = auto['id']

            # Récupérer données
            executions = await list_executions(automation_id)
            triggers = await crud.get_triggers(automation_id)
            steps = await crud.get_workflows(automation_id)

            # Calculer stats et health
            stats = calculate_automation_stats(executions)
            last_execution = format_last_execution(executions[0] if executions else None)
            health = await check_automation_health(auto, executions, triggers, steps)

            # Auto-disable si nécessaire
            if health['should_disable'] and auto.get('enabled'):
                await crud.update_automation(automation_id, enabled=False)
                auto['enabled'] = False

            enriched.append({
                **auto,
                'last_execution': last_execution,
                'triggers': triggers,
                'health_status': health['status'],
                'health_issues': health['issues'],
                'stats': stats
            })

        return enriched
