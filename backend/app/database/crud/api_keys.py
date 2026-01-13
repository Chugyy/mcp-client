# app/database/crud/api_keys.py

import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id
from app.core.utils.encryption import encrypt_api_key, decrypt_api_key

# ============================
# API KEYS
# ============================

async def create_api_key(plain_value: str, user_id: str, service_id: str) -> str:
    """
    Crée une clé API chiffrée.

    Args:
        plain_value: La clé API en clair
        user_id: ID de l'utilisateur propriétaire
        service_id: ID du service associé

    Returns:
        ID de la clé API créée (format: key_xxxxxx)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        key_id = generate_id('key')
        encrypted_value = encrypt_api_key(plain_value)

        await conn.execute(
            """INSERT INTO api_keys (id, encrypted_value, user_id, service_id)
               VALUES ($1, $2, $3, $4)""",
            key_id, encrypted_value, user_id, service_id
        )
        return key_id


async def get_api_key(key_id: str) -> Optional[Dict]:
    """
    Récupère une clé API par ID (valeur chiffrée).

    Args:
        key_id: ID de la clé API

    Returns:
        Dict contenant les informations de la clé (avec encrypted_value)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM api_keys WHERE id = $1", key_id)
        return dict(result) if result else None


async def get_api_key_decrypted(key_id: str) -> Optional[str]:
    """
    Récupère la valeur déchiffrée d'une clé API.

    Args:
        key_id: ID de la clé API

    Returns:
        La valeur déchiffrée de la clé ou None si non trouvée
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT encrypted_value FROM api_keys WHERE id = $1",
            key_id
        )
        if not result:
            return None

        return decrypt_api_key(result['encrypted_value'])


async def list_api_keys(user_id: Optional[str] = None) -> List[Dict]:
    """
    Liste les clés API (sans déchiffrer les valeurs).

    Args:
        user_id: ID de l'utilisateur (optionnel, filtre par user)

    Returns:
        Liste des clés API
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch(
                "SELECT * FROM api_keys WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
        else:
            rows = await conn.fetch("SELECT * FROM api_keys ORDER BY created_at DESC")
        return [dict(row) for row in rows]


async def update_api_key(key_id: str, plain_value: str) -> bool:
    """
    Met à jour une clé API (rotation de clé).

    Args:
        key_id: ID de la clé API
        plain_value: Nouvelle valeur en clair

    Returns:
        True si la mise à jour a réussi
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        encrypted_value = encrypt_api_key(plain_value)

        result = await conn.execute(
            "UPDATE api_keys SET encrypted_value = $1, updated_at = NOW() WHERE id = $2",
            encrypted_value, key_id
        )
        return int(result.split()[1]) > 0


async def delete_api_key(key_id: str) -> bool:
    """
    Supprime une clé API.

    Args:
        key_id: ID de la clé API

    Returns:
        True si la suppression a réussi
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM api_keys WHERE id = $1", key_id)
        return int(result.split()[1]) > 0


async def create_api_key_for_server(user_id: str, service_id: str, api_key_value: str) -> str:
    """
    Crée et encrypte une clé API pour un serveur MCP.

    Args:
        user_id: ID de l'utilisateur propriétaire
        service_id: ID du service MCP associé
        api_key_value: Valeur de la clé API en clair

    Returns:
        ID de la clé API créée (format: key_xxxxxx)
    """
    return await create_api_key(
        plain_value=api_key_value,
        user_id=user_id,
        service_id=service_id
    )
