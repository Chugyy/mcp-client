import asyncpg
import json
from typing import Optional, Dict, List
from datetime import datetime
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id


async def create_execution(
    automation_id: str,
    user_id: str,
    trigger_id: Optional[str] = None,
    status: str = 'pending',
    input_params: Optional[Dict] = None
) -> str:
    """Crée une exécution d'automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        execution_id = generate_id('execution')
        await conn.execute(
            """INSERT INTO automation.executions
               (id, automation_id, trigger_id, user_id, status, input_params, started_at)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())""",
            execution_id, automation_id, trigger_id, user_id, status,
            json.dumps(input_params or {})
        )
        return execution_id


async def update_execution_status(
    execution_id: str,
    status: str,
    result: Optional[Dict] = None,
    error: Optional[str] = None,
    completed_at: Optional[datetime] = None
) -> bool:
    """Met à jour le statut d'une exécution."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        update_fields = ["status = $1"]
        params = [status]
        param_count = 2

        if result is not None:
            update_fields.append(f"result = ${param_count}::jsonb")
            params.append(json.dumps(result))
            param_count += 1

        if error is not None:
            update_fields.append(f"error = ${param_count}")
            params.append(error)
            param_count += 1

        if completed_at is not None:
            update_fields.append(f"completed_at = ${param_count}")
            params.append(completed_at)
            param_count += 1
        elif status in ['completed', 'failed', 'cancelled']:
            update_fields.append("completed_at = NOW()")

        params.append(execution_id)
        query = f"UPDATE automation.executions SET {', '.join(update_fields)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0


async def create_step_log(
    execution_id: str,
    step_id: str,
    status: str,
    result: Optional[Dict] = None,
    error: Optional[str] = None,
    duration_ms: Optional[int] = None
) -> str:
    """Crée un log d'exécution pour une étape."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        log_id = generate_id('execution_step_log')
        await conn.execute(
            """INSERT INTO automation.execution_step_logs
               (id, execution_id, step_id, status, result, error, duration_ms, executed_at)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, NOW())""",
            log_id, execution_id, step_id, status, json.dumps(result) if result else None, error, duration_ms
        )
        return log_id


async def get_execution_step_logs(execution_id: str) -> List[Dict]:
    """Récupère tous les logs d'exécution, triés par executed_at."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM automation.execution_step_logs
               WHERE execution_id = $1
               ORDER BY executed_at ASC""",
            execution_id
        )
        logs = []
        for row in rows:
            log_dict = dict(row)
            # Parser le JSON de result si c'est une string
            if log_dict.get("result") and isinstance(log_dict["result"], str):
                try:
                    log_dict["result"] = json.loads(log_dict["result"])
                except json.JSONDecodeError:
                    pass  # Garder la string si le JSON est invalide
            logs.append(log_dict)
        return logs


async def get_execution(execution_id: str) -> Optional[Dict]:
    """Récupère une execution par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM automation.executions WHERE id = $1",
            execution_id
        )
        return dict(result) if result else None


async def list_executions(automation_id: str) -> List[Dict]:
    """Liste toutes les executions d'une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM automation.executions
               WHERE automation_id = $1
               ORDER BY started_at DESC""",
            automation_id
        )
        return [dict(row) for row in rows]


async def update_execution(execution_id: str, updates: Dict) -> bool:
    """Met à jour une execution avec des champs dynamiques."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        update_fields = []
        params = []
        param_count = 1

        for field, value in updates.items():
            if field == "paused_at" and value == "NOW()":
                update_fields.append(f"paused_at = NOW()")
            elif field == "execution_state":
                update_fields.append(f"execution_state = ${param_count}::jsonb")
                params.append(json.dumps(value))
                param_count += 1
            elif field == "status":
                update_fields.append(f"status = ${param_count}")
                params.append(value)
                param_count += 1
            else:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1

        if not update_fields:
            return False

        params.append(execution_id)
        query = f"UPDATE automation.executions SET {', '.join(update_fields)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0
