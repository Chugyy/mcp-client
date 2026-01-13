import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# SERVICES
# ============================

async def create_service(name: str, provider: str,
                         description: str = None, status: str = 'active') -> str:
    """Crée un service."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        service_id = generate_id('service')
        await conn.execute(
            """INSERT INTO services (id, name, provider, description, status)
               VALUES ($1, $2, $3, $4, $5)""",
            service_id, name, provider, description, status
        )
        return service_id

async def get_service(service_id: str) -> Optional[Dict]:
    """Récupère un service par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM services WHERE id = $1", service_id)
        return dict(result) if result else None

async def list_services(provider: Optional[str | List[str]] = None, status: Optional[str] = None) -> List[Dict]:
    """
    Liste tous les services avec filtres optionnels.

    Args:
        provider: Filtre par provider(s). Peut être une string unique ou une liste.
        status: Filtre par status (active, inactive, deprecated).

    Returns:
        Liste de dictionnaires représentant les services.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM services WHERE 1=1"
        params = []

        if provider:
            # Convertir en liste si c'est une string
            providers = [provider] if isinstance(provider, str) else provider

            # Générer les placeholders pour IN clause
            placeholders = ', '.join(f'${i+1}' for i in range(len(providers)))
            query += f" AND provider IN ({placeholders})"
            params.extend(providers)

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"

        query += " ORDER BY created_at DESC"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

async def update_service(service_id: str, name: str = None, provider: str = None,
                        description: str = None, status: str = None, logo_upload_id: str = None) -> bool:
    """Met à jour un service."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if provider is not None:
            updates.append(f"provider = ${param_count}")
            params.append(provider)
            param_count += 1

        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1

        if status is not None:
            updates.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        if logo_upload_id is not None:
            updates.append(f"logo_upload_id = ${param_count}")
            params.append(logo_upload_id)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(service_id)

        query = f"UPDATE services SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_service(service_id: str) -> bool:
    """Supprime un service."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM services WHERE id = $1", service_id)
        return int(result.split()[1]) > 0

async def get_service_by_name_and_provider(name: str, provider: str) -> Optional[Dict]:
    """Récupère un service par nom et provider."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM services WHERE name = $1 AND provider = $2",
            name, provider
        )
        return dict(result) if result else None
