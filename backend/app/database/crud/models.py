import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# MODELS
# ============================

async def create_model(service_id: str, model_name: str,
                      display_name: str = None, description: str = None,
                      enabled: bool = True) -> str:
    """Crée un modèle."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        model_id = generate_id('model')
        await conn.execute(
            """INSERT INTO models (id, service_id, model_name, display_name, description, enabled)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            model_id, service_id, model_name, display_name, description, enabled
        )
        return model_id

async def get_model(model_id: str) -> Optional[Dict]:
    """Récupère un modèle par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM models WHERE id = $1", model_id)
        return dict(result) if result else None

async def list_models(service_id: Optional[str] = None, enabled: Optional[bool] = None) -> List[Dict]:
    """Liste tous les modèles avec filtres optionnels."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM models WHERE 1=1"
        params = []

        if service_id:
            params.append(service_id)
            query += f" AND service_id = ${len(params)}"

        if enabled is not None:
            params.append(enabled)
            query += f" AND enabled = ${len(params)}"

        query += " ORDER BY created_at DESC"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

async def update_model(model_id: str, model_name: str = None,
                      display_name: str = None, description: str = None,
                      enabled: bool = None) -> bool:
    """Met à jour un modèle."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

        if model_name is not None:
            updates.append(f"model_name = ${param_count}")
            params.append(model_name)
            param_count += 1

        if display_name is not None:
            updates.append(f"display_name = ${param_count}")
            params.append(display_name)
            param_count += 1

        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1

        if enabled is not None:
            updates.append(f"enabled = ${param_count}")
            params.append(enabled)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(model_id)

        query = f"UPDATE models SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_model(model_id: str) -> bool:
    """Supprime un modèle."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM models WHERE id = $1", model_id)
        return int(result.split()[1]) > 0

async def get_model_by_name(service_id: str, model_name: str) -> Optional[Dict]:
    """Récupère un modèle par service_id et model_name."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM models WHERE service_id = $1 AND model_name = $2",
            service_id, model_name
        )
        return dict(result) if result else None

async def list_models_with_service() -> List[Dict]:
    """Liste tous les modèles avec leurs informations de service (JOIN + logo)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT m.*,
                   s.name as service_name,
                   s.provider,
                   s.status as service_status,
                   s.logo_upload_id,
                   u.file_path as logo_url
            FROM models m
            INNER JOIN services s ON m.service_id = s.id
            LEFT JOIN uploads u ON u.id = s.logo_upload_id
            WHERE m.enabled = true AND s.status = 'active'
            ORDER BY s.provider, m.model_name
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

async def list_models_for_user(user_id: str) -> List[Dict]:
    """
    Liste uniquement les modèles disponibles pour un utilisateur.
    Filtre par providers activés avec clé API configurée.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Liste des modèles avec infos service (incluant logo_url)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT DISTINCT m.*,
                   s.name as service_name,
                   s.provider,
                   s.status as service_status,
                   s.logo_upload_id,
                   u.file_path as logo_url
            FROM models m
            INNER JOIN services s ON m.service_id = s.id
            INNER JOIN user_providers up ON up.service_id = s.id
            LEFT JOIN uploads u ON u.id = s.logo_upload_id
            WHERE up.user_id = $1
              AND up.enabled = true
              AND up.api_key_id IS NOT NULL
              AND m.enabled = true
              AND s.status = 'active'
            ORDER BY s.provider, m.model_name
        """
        rows = await conn.fetch(query, user_id)
        return [dict(row) for row in rows]
