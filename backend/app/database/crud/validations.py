import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# VALIDATIONS
# ============================

async def create_validation(user_id: str, title: str, source: str, process: str,
                           description: str = None, agent_id: str = None,
                           status: str = 'pending') -> str:
    """Crée une validation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        validation_id = generate_id('validation')
        await conn.execute(
            """INSERT INTO validations (id, user_id, agent_id, title, description,
               source, process, status)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            validation_id, user_id, agent_id, title, description, source, process, status
        )
        return validation_id

async def get_validation(validation_id: str) -> Optional[Dict]:
    """Récupère une validation par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM validations WHERE id = $1", validation_id)
        return dict(result) if result else None

async def list_validations_by_user(user_id: str, status: str = None) -> List[Dict]:
    """Liste les validations d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM validations WHERE user_id = $1 AND status = $2 ORDER BY created_at DESC",
                user_id, status
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM validations WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
        return [dict(row) for row in rows]

async def update_validation_status(validation_id: str, status: str) -> bool:
    """Met à jour le statut d'une validation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE validations SET status = $1, updated_at = NOW() WHERE id = $2",
            status, validation_id
        )
        return int(result.split()[1]) > 0

async def delete_validation(validation_id: str) -> bool:
    """Supprime une validation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM validations WHERE id = $1", validation_id)
        return int(result.split()[1]) > 0

async def get_validations_by_execution(execution_id: str) -> List[Dict]:
    """Récupère toutes les validations d'une execution."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM validations WHERE execution_id = $1 ORDER BY created_at DESC",
            execution_id
        )
        return [dict(row) for row in rows]

async def get_pending_validations_for_chat(chat_id: str):
    """Récupère toutes les validations pending pour un chat."""
    from app.database.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, tool_name, server_id
               FROM validations
               WHERE chat_id = $1 AND status = 'pending'""",
            chat_id
        )
        return [dict(row) for row in rows]


async def cancel_all_pending_validations(chat_id: str, reason: str = "cascade_cancellation") -> int:
    """
    Annule toutes les validations pending pour un chat donné.

    Args:
        chat_id: ID du chat
        reason: Raison de l'annulation (logguée mais non stockée en DB)

    Returns:
        Nombre de validations annulées
    """
    from config.logger import logger

    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch(
            """
            UPDATE validations
            SET status = 'cancelled',
                updated_at = NOW()
            WHERE chat_id = $1
            AND status = 'pending'
            RETURNING id
            """,
            chat_id
        )
        cancelled_ids = [row['id'] for row in result]

        logger.info(f"Cancelled {len(cancelled_ids)} pending validations for chat {chat_id} (reason: {reason})")
        return len(cancelled_ids)


# ============================
# HELPERS POUR VALIDATION MANAGER
# ============================

async def count_validations_by_user(user_id: str, status: Optional[str] = None) -> int:
    """
    Compte les validations d'un utilisateur avec filtre optionnel sur le statut.

    Args:
        user_id: ID de l'utilisateur
        status: Statut à filtrer (optionnel)

    Returns:
        Nombre de validations

    Examples:
        >>> await count_validations_by_user('user_123')
        42
        >>> await count_validations_by_user('user_123', 'pending')
        5
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM validations WHERE user_id = $1 AND status = $2",
                user_id, status
            )
        else:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM validations WHERE user_id = $1",
                user_id
            )
        return result or 0


async def get_user(user_id: str) -> Optional[Dict]:
    """
    Récupère un utilisateur par ID.

    Utilisé pour récupérer le User object dans les background tasks.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Dict avec les données de l'utilisateur ou None si non trouvé

    Examples:
        >>> user = await get_user('user_123')
        >>> user['email']
        'test@example.com'
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(result) if result else None
