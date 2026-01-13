"""
CRUD operations for refresh_tokens table
"""

from typing import Optional, Dict, List
from datetime import datetime
from app.database.db import get_pool
from config.logger import logger

# ============================
# REFRESH TOKENS
# ============================

async def create_refresh_token(user_id: str, token_hash: str, expires_at: datetime) -> str:
    """
    Crée un refresh token en base de données.

    Args:
        user_id: ID de l'utilisateur
        token_hash: Hash SHA256 du token
        expires_at: Date d'expiration du token

    Returns:
        ID du refresh token créé (format: rft_xxxxxx)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
               VALUES ($1, $2, $3)
               RETURNING id""",
            user_id, token_hash, expires_at
        )
        token_id = result['id']
        logger.debug(f"Refresh token created: {token_id} for user {user_id}")
        return token_id


async def get_refresh_token_by_hash(token_hash: str) -> Optional[Dict]:
    """
    Récupère un refresh token par son hash.

    Args:
        token_hash: Hash SHA256 du token

    Returns:
        Dict avec les données du token ou None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM refresh_tokens WHERE token_hash = $1",
            token_hash
        )
        return dict(result) if result else None


async def revoke_refresh_token(token_hash: str) -> bool:
    """
    Révoque un refresh token (logout).

    Args:
        token_hash: Hash SHA256 du token

    Returns:
        True si le token a été révoqué, False sinon
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE refresh_tokens
               SET revoked = TRUE, updated_at = CURRENT_TIMESTAMP
               WHERE token_hash = $1 AND revoked = FALSE""",
            token_hash
        )
        # result est du type "UPDATE n" où n est le nombre de lignes modifiées
        rows_affected = int(result.split()[-1])
        if rows_affected > 0:
            logger.info(f"Refresh token revoked: {token_hash[:16]}...")
            return True
        return False


async def revoke_all_user_tokens(user_id: str) -> int:
    """
    Révoque tous les refresh tokens d'un utilisateur (logout all devices).

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Nombre de tokens révoqués
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE refresh_tokens
               SET revoked = TRUE, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = $1 AND revoked = FALSE""",
            user_id
        )
        rows_affected = int(result.split()[-1])
        logger.info(f"Revoked {rows_affected} tokens for user {user_id}")
        return rows_affected


async def delete_expired_tokens() -> int:
    """
    Supprime les refresh tokens expirés (job de nettoyage).

    Returns:
        Nombre de tokens supprimés
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """DELETE FROM refresh_tokens
               WHERE expires_at < CURRENT_TIMESTAMP"""
        )
        rows_affected = int(result.split()[-1])
        if rows_affected > 0:
            logger.info(f"Deleted {rows_affected} expired refresh tokens")
        return rows_affected


async def get_user_active_tokens(user_id: str) -> List[Dict]:
    """
    Récupère tous les refresh tokens actifs d'un utilisateur.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Liste des tokens actifs (non révoqués et non expirés)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        results = await conn.fetch(
            """SELECT id, created_at, expires_at
               FROM refresh_tokens
               WHERE user_id = $1
                 AND revoked = FALSE
                 AND expires_at > CURRENT_TIMESTAMP
               ORDER BY created_at DESC""",
            user_id
        )
        return [dict(row) for row in results]


async def count_user_active_tokens(user_id: str) -> int:
    """
    Compte le nombre de tokens actifs pour un utilisateur.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Nombre de tokens actifs
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            """SELECT COUNT(*)
               FROM refresh_tokens
               WHERE user_id = $1
                 AND revoked = FALSE
                 AND expires_at > CURRENT_TIMESTAMP""",
            user_id
        )
        return result or 0
