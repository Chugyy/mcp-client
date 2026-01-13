"""CRUD operations for logs table."""

import json
from typing import Optional, Dict, List, Any
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id


async def create_log(
    user_id: str,
    log_type: str,
    data: Dict[str, Any],
    agent_id: Optional[str] = None,
    chat_id: Optional[str] = None
) -> str:
    """
    Crée un log générique.

    Args:
        user_id: ID de l'utilisateur
        log_type: Type de log (tool_call, validation, stream_stop, error)
        data: Données du log (format flexible selon le type)
        agent_id: ID de l'agent (optionnel)
        chat_id: ID du chat (optionnel)

    Returns:
        ID du log créé

    Examples:
        # Tool call log
        await create_log(
            user_id="usr_xxx",
            log_type="tool_call",
            data={
                "tool_name": "send_email",
                "server_id": "srv_xxx",
                "args": {"to": "user@example.com"},
                "result": {"success": True},
                "status": "executed",
                "always_allow": False
            },
            chat_id="cht_xxx"
        )

        # Validation log
        await create_log(
            user_id="usr_xxx",
            log_type="validation",
            data={
                "validation_id": "val_xxx",
                "action": "approved",
                "tool_name": "send_email"
            },
            chat_id="cht_xxx"
        )
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        log_id = generate_id('log')
        await conn.execute(
            """INSERT INTO logs (id, user_id, agent_id, chat_id, type, data)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb)""",
            log_id, user_id, agent_id, chat_id, log_type, json.dumps(data)
        )
        return log_id


async def get_log(log_id: str) -> Optional[Dict]:
    """Récupère un log par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM logs WHERE id = $1", log_id)
        return dict(result) if result else None


async def list_logs_by_chat(
    chat_id: str,
    log_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Liste les logs d'un chat.

    Args:
        chat_id: ID du chat
        log_type: Type de log à filtrer (optionnel)
        limit: Nombre maximum de résultats
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if log_type:
            rows = await conn.fetch(
                """SELECT * FROM logs
                   WHERE chat_id = $1 AND type = $2
                   ORDER BY created_at DESC
                   LIMIT $3""",
                chat_id, log_type, limit
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM logs
                   WHERE chat_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2""",
                chat_id, limit
            )
        return [dict(row) for row in rows]


async def list_logs_by_user(
    user_id: str,
    log_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Liste les logs d'un utilisateur.

    Args:
        user_id: ID de l'utilisateur
        log_type: Type de log à filtrer (optionnel)
        limit: Nombre maximum de résultats
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if log_type:
            rows = await conn.fetch(
                """SELECT * FROM logs
                   WHERE user_id = $1 AND type = $2
                   ORDER BY created_at DESC
                   LIMIT $3""",
                user_id, log_type, limit
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM logs
                   WHERE user_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2""",
                user_id, limit
            )
        return [dict(row) for row in rows]


async def check_tool_cache(
    user_id: str,
    tool_name: str,
    server_id: str,
    agent_id: Optional[str] = None
) -> bool:
    """
    Vérifie si un tool est dans le cache (always_allow=true).

    Args:
        user_id: ID de l'utilisateur
        tool_name: Nom du tool
        server_id: ID du serveur MCP
        agent_id: ID de l'agent (optionnel)

    Returns:
        True si le tool est autorisé en permanence, False sinon

    Note:
        Cette fonction utilise l'index idx_logs_tool_cache pour des performances optimales.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """SELECT id FROM logs
               WHERE type = 'tool_call'
                 AND user_id = $1
                 AND ($2::TEXT IS NULL OR agent_id = $2)
                 AND data->>'tool_name' = $3
                 AND data->>'server_id' = $4
                 AND (data->>'always_allow')::boolean = true
               LIMIT 1""",
            user_id, agent_id, tool_name, server_id
        )
        return result is not None


async def get_tool_cache_entry(
    user_id: str,
    tool_name: str,
    server_id: str,
    agent_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Récupère l'entrée de cache complète pour un tool.

    Utile pour afficher les métadonnées du cache (date de création, nombre d'utilisations, etc.)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """SELECT * FROM logs
               WHERE type = 'tool_call'
                 AND user_id = $1
                 AND ($2::TEXT IS NULL OR agent_id = $2)
                 AND data->>'tool_name' = $3
                 AND data->>'server_id' = $4
                 AND (data->>'always_allow')::boolean = true
               ORDER BY created_at DESC
               LIMIT 1""",
            user_id, agent_id, tool_name, server_id
        )
        return dict(result) if result else None


async def delete_tool_cache(
    user_id: str,
    tool_name: str,
    server_id: str,
    agent_id: Optional[str] = None
) -> bool:
    """
    Supprime une entrée de cache (révoque l'autorisation permanente).

    Returns:
        True si une entrée a été supprimée, False sinon
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """DELETE FROM logs
               WHERE type = 'tool_call'
                 AND user_id = $1
                 AND ($2::TEXT IS NULL OR agent_id = $2)
                 AND data->>'tool_name' = $3
                 AND data->>'server_id' = $4
                 AND (data->>'always_allow')::boolean = true""",
            user_id, agent_id, tool_name, server_id
        )
        return int(result.split()[1]) > 0


async def count_tool_executions(
    user_id: str,
    tool_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    chat_id: Optional[str] = None
) -> int:
    """
    Compte le nombre d'exécutions de tools.

    Args:
        user_id: ID de l'utilisateur
        tool_name: Nom du tool (optionnel, compte tous les tools si absent)
        agent_id: ID de l'agent (optionnel)
        chat_id: ID du chat (optionnel)

    Returns:
        Nombre total d'exécutions
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """SELECT COUNT(*) FROM logs
               WHERE type = 'tool_call'
                 AND user_id = $1"""
        params = [user_id]

        if agent_id:
            query += " AND agent_id = $" + str(len(params) + 1)
            params.append(agent_id)

        if chat_id:
            query += " AND chat_id = $" + str(len(params) + 1)
            params.append(chat_id)

        if tool_name:
            query += " AND data->>'tool_name' = $" + str(len(params) + 1)
            params.append(tool_name)

        result = await conn.fetchval(query, *params)
        return result or 0


async def get_logs_by_validation_id(validation_id: str) -> List[Dict]:
    """
    Récupère tous les logs associés à une validation.

    Args:
        validation_id: ID de la validation

    Returns:
        Liste des logs (action: approved/rejected/feedback avec détails)

    Example:
        [
            {
                "id": "log_xxx",
                "type": "validation",
                "data": {
                    "validation_id": "val_xxx",
                    "action": "rejected",
                    "tool_name": "send_email",
                    "reason": "Email address is invalid"
                },
                "created_at": "2025-12-04T10:30:00Z"
            }
        ]
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM logs
               WHERE type = 'validation'
                 AND data->>'validation_id' = $1
               ORDER BY created_at ASC""",
            validation_id
        )
        return [dict(row) for row in rows]
