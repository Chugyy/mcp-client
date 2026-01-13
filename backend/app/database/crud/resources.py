import asyncpg
import json
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# RESOURCES
# ============================

async def create_resource(
    user_id: str,
    name: str,
    description: Optional[str] = None,
    enabled: bool = True,
    embedding_model: str = 'text-embedding-3-large',
    embedding_dim: int = 3072,
    is_system: bool = False  # Note: is_system parameter accepted but not persisted (no DB column)
) -> str:
    """Crée une nouvelle resource."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        resource_id = generate_id('resource')
        await conn.execute(
            """INSERT INTO resources (id, user_id, name, description, enabled, embedding_model, embedding_dim)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            resource_id, user_id, name, description, enabled, embedding_model, embedding_dim
        )
        return resource_id

async def get_resource(resource_id: str) -> Optional[Dict]:
    """Récupère une ressource par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM resources WHERE id = $1", resource_id)
        return dict(result) if result else None

# DEPRECATED: Cette fonction retourne TOUTES les ressources du système.
# Utilisez list_resources_by_user() pour filtrer par utilisateur.
# Cette fonction ne devrait être utilisée que par les admins.
async def list_resources(enabled_only: bool = False) -> List[Dict]:
    """
    Liste TOUTES les ressources du système (admin only).

    ⚠️ DEPRECATED: Utilisez list_resources_by_user() pour filtrer par user.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                "SELECT * FROM resources WHERE enabled = TRUE ORDER BY created_at DESC"
            )
        else:
            rows = await conn.fetch("SELECT * FROM resources ORDER BY created_at DESC")
        return [dict(row) for row in rows]

async def list_resources_by_user(user_id: str, enabled_only: bool = False) -> List[Dict]:
    """Liste toutes les ressources d'un utilisateur + ressources publiques internes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                """SELECT * FROM resources
                   WHERE (user_id = $1 OR (user_id = '__internal__' AND is_public = true)) AND enabled = TRUE
                   ORDER BY user_id = '__internal__' DESC, created_at DESC""",
                user_id
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM resources
                   WHERE user_id = $1 OR (user_id = '__internal__' AND is_public = true)
                   ORDER BY user_id = '__internal__' DESC, created_at DESC""",
                user_id
            )
        return [dict(row) for row in rows]

async def update_resource(
    resource_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None
) -> bool:
    """Met à jour une resource (champs métier uniquement)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = [resource_id]
        param_count = 2

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
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
            return True

        updates.append("updated_at = NOW()")
        query = f"UPDATE resources SET {', '.join(updates)} WHERE id = $1"

        await conn.execute(query, *params)
        return True

async def update_resource_status(
    resource_id: str,
    status: str,
    chunk_count: Optional[int] = None,
    error_message: Optional[str] = None
) -> bool:
    """Met à jour le status RAG d'une resource."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = ["status = $2"]
        params = [resource_id, status]
        param_count = 3

        if chunk_count is not None:
            updates.append(f"chunk_count = ${param_count}")
            params.append(chunk_count)
            param_count += 1

        if status == 'ready':
            updates.append("indexed_at = NOW()")

        if error_message is not None:
            updates.append(f"error_message = ${param_count}")
            params.append(error_message)
            param_count += 1

        updates.append("updated_at = NOW()")

        query = f"UPDATE resources SET {', '.join(updates)} WHERE id = $1"
        await conn.execute(query, *params)
        return True

async def delete_resource(resource_id: str) -> bool:
    """Supprime une ressource."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM resources WHERE id = $1", resource_id)
        return int(result.split()[1]) > 0

# ============================
# IMPACT ANALYSIS
# ============================

async def get_agents_using_resource(resource_id: str) -> List[Dict]:
    """
    Récupère tous les agents qui utilisent cette ressource.

    Returns:
        Liste d'agents avec leurs configurations complètes.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT DISTINCT a.id, a.name, a.user_id
               FROM agents a
               JOIN configurations c ON c.agent_id = a.id
               WHERE c.entity_type = 'resource' AND c.entity_id = $1""",
            resource_id
        )
        return [dict(row) for row in rows]

async def get_resource_deletion_impact(resource_id: str) -> Dict:
    """
    Calcule l'impact de la suppression d'une ressource.

    Returns:
        {
            "agents_to_delete": [...],      # Agents qui seront supprimés
            "agents_to_update": [...],      # Agents dont config sera retirée
            "chats_to_delete": int,         # Total de chats impactés
            "configurations_to_delete": int # Nombre de configs supprimées
        }
    """
    from app.database.crud import chats as crud_chats

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer tous les agents utilisant cette ressource
        agents_using_resource = await get_agents_using_resource(resource_id)

        agents_to_delete = []
        agents_to_update = []
        total_chats = 0

        for agent in agents_using_resource:
            agent_id = agent['id']

            # Compter les configurations de cet agent
            config_count = await conn.fetchval(
                "SELECT COUNT(*) FROM configurations WHERE agent_id = $1",
                agent_id
            )

            # Si l'agent n'a qu'une seule config (celle de la ressource à supprimer)
            if config_count == 1:
                agents_to_delete.append({
                    "id": agent_id,
                    "name": agent['name']
                })
                # Compter les chats de cet agent
                chat_count = await crud_chats.count_chats_by_agent(agent_id)
                total_chats += chat_count
            else:
                agents_to_update.append({
                    "id": agent_id,
                    "name": agent['name']
                })

        # Compter le total de configurations à supprimer
        config_count = await conn.fetchval(
            """SELECT COUNT(*) FROM configurations
               WHERE entity_type = 'resource' AND entity_id = $1""",
            resource_id
        )

        return {
            "agents_to_delete": agents_to_delete,
            "agents_to_update": agents_to_update,
            "chats_to_delete": total_chats,
            "configurations_to_delete": config_count or 0
        }


# ============================
# VALIDATION HELPERS
# ============================

async def get_resource_by_name_and_user(
    name: str,
    user_id: str
) -> Optional[Dict]:
    """
    Récupère une ressource par nom et utilisateur.
    Utilisé pour vérifier l'unicité du nom.

    Args:
        name: Nom de la ressource
        user_id: ID de l'utilisateur

    Returns:
        Resource dict ou None si non trouvée
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM resources
            WHERE name = $1 AND user_id = $2
            LIMIT 1
            """,
            name,
            user_id
        )
        return dict(row) if row else None


async def count_resources_by_user(user_id: str) -> int:
    """
    Compte le nombre de ressources d'un utilisateur.
    Utilisé pour vérifier le quota.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Nombre de ressources
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM resources WHERE user_id = $1",
            user_id
        )
        return count or 0
