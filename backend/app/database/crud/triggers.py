import asyncpg
import json
from typing import Dict, List, Optional
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id
from app.core.utils.security import hash_webhook_secret


async def create_trigger(
    automation_id: str,
    trigger_type: str,
    config: Dict,
    enabled: bool = True
) -> str:
    """Crée un trigger pour une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        trigger_id = generate_id('trigger')

        # Hash le secret si trigger_type = webhook
        if trigger_type == "webhook" and "secret" in config:
            config = config.copy()  # Ne pas modifier l'original
            config["secret"] = hash_webhook_secret(config["secret"])

        await conn.execute(
            """INSERT INTO automation.triggers (id, automation_id, trigger_type, config, enabled)
               VALUES ($1, $2, $3, $4::jsonb, $5)""",
            trigger_id, automation_id, trigger_type, json.dumps(config), enabled
        )
        return trigger_id


async def get_trigger(trigger_id: str) -> Optional[Dict]:
    """Récupère un trigger par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM automation.triggers WHERE id = $1",
            trigger_id
        )
        if not result:
            return None

        trigger = dict(result)
        # Parser le JSON si c'est une string
        if isinstance(trigger.get('config'), str):
            trigger['config'] = json.loads(trigger['config'])

        # Masquer le secret webhook
        if trigger.get('trigger_type') == 'webhook' and 'secret' in trigger.get('config', {}):
            trigger['config']['secret'] = '***'

        return trigger


async def get_triggers(automation_id: str) -> List[Dict]:
    """Récupère tous les triggers d'une automation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM automation.triggers
               WHERE automation_id = $1
               ORDER BY created_at DESC""",
            automation_id
        )
        triggers = []
        for row in rows:
            trigger = dict(row)
            # Parser le JSON si c'est une string
            if isinstance(trigger.get('config'), str):
                trigger['config'] = json.loads(trigger['config'])

            # Masquer le secret webhook
            if trigger.get('trigger_type') == 'webhook' and 'secret' in trigger.get('config', {}):
                trigger['config']['secret'] = '***'

            triggers.append(trigger)
        return triggers


async def update_trigger(trigger_id: str, **updates) -> bool:
    """Met à jour un trigger."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        update_fields = []
        params = []
        param_count = 1

        for field, value in updates.items():
            if value is not None:
                # Hash le secret si on met à jour un webhook
                if field == "config" and isinstance(value, dict) and "secret" in value:
                    value = value.copy()
                    value["secret"] = hash_webhook_secret(value["secret"])

                if field == "config":
                    update_fields.append(f"{field} = ${param_count}::jsonb")
                    params.append(json.dumps(value))
                else:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                param_count += 1

        if not update_fields:
            return False

        params.append(trigger_id)
        query = f"UPDATE automation.triggers SET {', '.join(update_fields)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0


async def delete_trigger(trigger_id: str) -> bool:
    """Supprime un trigger."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM automation.triggers WHERE id = $1",
            trigger_id
        )
        return int(result.split()[1]) > 0
