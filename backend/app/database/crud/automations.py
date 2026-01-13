import asyncpg
import json
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id


async def create_automation(
    user_id: str,
    name: str,
    description: Optional[str] = None,
    is_system: bool = False,
    enabled: bool = True
) -> str:
    """Crée une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        automation_id = generate_id('automation')
        await conn.execute(
            """INSERT INTO automation.automations (id, user_id, name, description, is_system, enabled)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            automation_id, user_id, name, description, is_system, enabled
        )
        return automation_id


async def get_automation(automation_id: str) -> Optional[Dict]:
    """Récupère une automation par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM automation.automations WHERE id = $1",
            automation_id
        )
        return dict(result) if result else None


async def list_automations(user_id: str) -> List[Dict]:
    """Liste les automations d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM automation.automations
               WHERE user_id = $1
               ORDER BY created_at DESC""",
            user_id
        )
        return [dict(row) for row in rows]


async def update_automation(automation_id: str, **updates) -> bool:
    """Met à jour une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        update_fields = []
        params = []
        param_count = 1

        for field, value in updates.items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1

        if not update_fields:
            return False

        update_fields.append("updated_at = NOW()")
        params.append(automation_id)

        query = f"UPDATE automation.automations SET {', '.join(update_fields)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0


async def delete_automation(automation_id: str) -> bool:
    """Supprime une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM automation.automations WHERE id = $1",
            automation_id
        )
        return int(result.split()[1]) > 0


async def list_cron_automations() -> List[Dict]:
    """Liste toutes les automations avec des triggers CRON actifs."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT DISTINCT a.*
               FROM automation.automations a
               JOIN automation.triggers t ON t.automation_id = a.id
               WHERE t.trigger_type = 'cron'
               AND t.enabled = true
               AND a.enabled = true
               ORDER BY a.created_at DESC"""
        )
        return [dict(row) for row in rows]


async def count_automations_by_user(user_id: str) -> int:
    """Compte les automations d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM automation.automations WHERE user_id = $1",
            user_id
        )
        return result or 0


async def get_automation_by_name_and_user(name: str, user_id: str) -> Optional[Dict]:
    """Récupère une automation par nom et user_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM automation.automations WHERE name = $1 AND user_id = $2",
            name, user_id
        )
        return dict(result) if result else None


# Import workflow steps functions from dedicated module
from app.database.crud.workflow_steps import (
    create_workflow_step,
    get_workflow_step,
    get_workflow_steps,
    update_workflow_step,
    delete_workflow_step
)

# Import triggers functions from dedicated module
from app.database.crud.triggers import (
    create_trigger,
    get_trigger,
    get_triggers,
    update_trigger,
    delete_trigger
)

# Aliases for backward compatibility
async def get_workflows(automation_id: str) -> List[Dict]:
    """Alias de get_workflow_steps."""
    return await get_workflow_steps(automation_id)


async def list_workflow_steps(automation_id: str) -> List[Dict]:
    """Alias de get_workflow_steps."""
    return await get_workflow_steps(automation_id)


async def list_triggers(automation_id: str) -> List[Dict]:
    """Alias de get_triggers."""
    return await get_triggers(automation_id)
