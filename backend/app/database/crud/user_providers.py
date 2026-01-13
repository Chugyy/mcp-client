# app/database/crud/user_providers.py

import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# USER PROVIDERS
# ============================

async def create_user_provider(user_id: str, service_id: str,
                               api_key_id: str = None, enabled: bool = True) -> str:
    """
    Crée une association user ↔ service (provider).

    Args:
        user_id: ID de l'utilisateur
        service_id: ID du service (provider LLM)
        api_key_id: ID de la clé API (optionnel)
        enabled: Provider activé ou non

    Returns:
        ID du user_provider créé (format: upr_xxxxxx)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        provider_id = generate_id('user_provider')
        await conn.execute(
            """INSERT INTO user_providers (id, user_id, service_id, api_key_id, enabled)
               VALUES ($1, $2, $3, $4, $5)""",
            provider_id, user_id, service_id, api_key_id, enabled
        )
        return provider_id


async def get_user_provider(provider_id: str) -> Optional[Dict]:
    """Récupère un user_provider par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM user_providers WHERE id = $1",
            provider_id
        )
        return dict(result) if result else None


async def get_user_provider_by_service(user_id: str, service_id: str) -> Optional[Dict]:
    """Récupère un user_provider par user_id et service_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM user_providers WHERE user_id = $1 AND service_id = $2",
            user_id, service_id
        )
        return dict(result) if result else None


async def list_user_providers(user_id: str, enabled: Optional[bool] = None) -> List[Dict]:
    """
    Liste tous les providers d'un utilisateur avec informations de service.

    Args:
        user_id: ID de l'utilisateur
        enabled: Filtrer par enabled (optionnel)

    Returns:
        Liste des providers avec infos service (JOIN)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT
                up.*,
                s.name as service_name,
                s.provider,
                s.status as service_status
            FROM user_providers up
            INNER JOIN services s ON up.service_id = s.id
            WHERE up.user_id = $1
        """
        params = [user_id]

        if enabled is not None:
            params.append(enabled)
            query += f" AND up.enabled = ${len(params)}"

        query += " ORDER BY s.provider, s.name"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def update_user_provider(provider_id: str, api_key_id: str = None,
                               enabled: bool = None) -> bool:
    """
    Met à jour un user_provider.

    Args:
        provider_id: ID du user_provider
        api_key_id: Nouvelle clé API (optionnel)
        enabled: Nouveau statut enabled (optionnel)

    Returns:
        True si la mise à jour a réussi
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

        if api_key_id is not None:
            updates.append(f"api_key_id = ${param_count}")
            params.append(api_key_id)
            param_count += 1

        if enabled is not None:
            updates.append(f"enabled = ${param_count}")
            params.append(enabled)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(provider_id)

        query = f"UPDATE user_providers SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0


async def delete_user_provider(provider_id: str) -> bool:
    """Supprime un user_provider."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_providers WHERE id = $1",
            provider_id
        )
        return int(result.split()[1]) > 0
