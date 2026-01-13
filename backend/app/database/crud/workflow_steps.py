import asyncpg
import json
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id


async def create_workflow_step(
    automation_id: str,
    step_order: int,
    step_name: str,
    step_type: str,
    step_subtype: str,
    config: Dict,
    run_condition: Optional[str] = None,
    enabled: bool = True
) -> str:
    """Crée une étape de workflow."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        step_id = generate_id('workflow_step')
        await conn.execute(
            """INSERT INTO automation.workflow_steps
               (id, automation_id, step_order, step_name, step_type, step_subtype,
                config, run_condition, enabled)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)""",
            step_id, automation_id, step_order, step_name, step_type,
            step_subtype, json.dumps(config), run_condition, enabled
        )
        return step_id


async def get_workflow_step(step_id: str) -> Optional[Dict]:
    """Récupère une étape de workflow par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM automation.workflow_steps WHERE id = $1",
            step_id
        )
        if not result:
            return None

        step = dict(result)
        # Parser le JSON si c'est une string
        if isinstance(step.get('config'), str):
            step['config'] = json.loads(step['config'])
        return step


async def get_workflow_steps(automation_id: str) -> List[Dict]:
    """Récupère toutes les étapes d'une automation, triées par step_order."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM automation.workflow_steps
               WHERE automation_id = $1
               ORDER BY step_order ASC""",
            automation_id
        )
        steps = []
        for row in rows:
            step = dict(row)
            # Parser le JSON si c'est une string
            if isinstance(step.get('config'), str):
                step['config'] = json.loads(step['config'])
            steps.append(step)
        return steps


async def update_workflow_step(step_id: str, **updates) -> bool:
    """Met à jour une étape de workflow."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        update_fields = []
        params = []
        param_count = 1

        for field, value in updates.items():
            if value is not None:
                if field == "config":
                    update_fields.append(f"{field} = ${param_count}::jsonb")
                    params.append(json.dumps(value))
                else:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                param_count += 1

        if not update_fields:
            return False

        params.append(step_id)
        query = f"UPDATE automation.workflow_steps SET {', '.join(update_fields)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0


async def delete_workflow_step(step_id: str) -> bool:
    """Supprime une étape de workflow."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM automation.workflow_steps WHERE id = $1",
            step_id
        )
        return int(result.split()[1]) > 0
