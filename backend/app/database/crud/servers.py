import asyncpg
import json
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# MCP SERVERS
# ============================

async def create_server(
    name: str,
    url: str = None,
    auth_type: str = None,
    description: str = None,
    api_key_id: str = None,
    enabled: bool = True,
    status: str = 'pending',
    user_id: str = None,
    type: str = 'http',
    args: list = None,
    env: dict = None,
    service_id: str = None
) -> str:
    """Crée un serveur MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        server_id = generate_id('server')

        # Convert args/env to JSON for JSONB columns
        args_json = json.dumps(args or [])
        env_json = json.dumps(env or {})

        await conn.execute(
            """INSERT INTO servers
               (id, name, description, type, url, auth_type, service_id, api_key_id,
                args, env, enabled, status, user_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11, $12, $13)""",
            server_id, name, description, type, url, auth_type, service_id, api_key_id,
            args_json, env_json, enabled, status, user_id
        )
        return server_id

async def get_server(server_id: str) -> Optional[Dict]:
    """Récupère un serveur MCP par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM servers WHERE id = $1", server_id)
        return dict(result) if result else None

async def list_servers(enabled_only: bool = False) -> List[Dict]:
    """Liste tous les serveurs MCP (DEPRECATED: use list_servers_by_user)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                "SELECT * FROM servers WHERE enabled = TRUE ORDER BY created_at DESC"
            )
        else:
            rows = await conn.fetch("SELECT * FROM servers ORDER BY created_at DESC")
        return [dict(row) for row in rows]

async def list_servers_by_user(user_id: str, enabled_only: bool = False) -> List[Dict]:
    """Liste tous les serveurs MCP d'un utilisateur + serveurs publics internes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                """SELECT * FROM servers
                   WHERE (user_id = $1 OR (user_id = '__internal__' AND is_public = true)) AND enabled = TRUE
                   ORDER BY user_id = '__internal__' DESC, created_at DESC""",
                user_id
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM servers
                   WHERE user_id = $1 OR (user_id = '__internal__' AND is_public = true)
                   ORDER BY user_id = '__internal__' DESC, created_at DESC""",
                user_id
            )
        return [dict(row) for row in rows]

async def update_server(server_id: str, name: str = None, description: str = None,
                       url: str = None, auth_type: str = None, service_id: str = None,
                       enabled: bool = None) -> bool:
    """Met à jour un serveur MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1

        if url is not None:
            updates.append(f"url = ${param_count}")
            params.append(url)
            param_count += 1

        if auth_type is not None:
            updates.append(f"auth_type = ${param_count}")
            params.append(auth_type)
            param_count += 1

        if service_id is not None:
            updates.append(f"service_id = ${param_count}")
            params.append(service_id)
            param_count += 1

        if enabled is not None:
            updates.append(f"enabled = ${param_count}")
            params.append(enabled)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(server_id)

        query = f"UPDATE servers SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_server(server_id: str) -> bool:
    """Supprime un serveur MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM servers WHERE id = $1", server_id)
        return int(result.split()[1]) > 0

async def update_server_status(server_id: str, status: str,
                               status_message: str = None) -> bool:
    """Met à jour uniquement le status d'un serveur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE servers
               SET status = $1, status_message = $2, last_health_check = NOW(), updated_at = NOW()
               WHERE id = $3""",
            status, status_message, server_id
        )
        return int(result.split()[1]) > 0

# ============================
# MCP TOOLS
# ============================

async def create_tool(server_id: str, name: str, description: str = None,
                     input_schema: dict = None, enabled: bool = True) -> str:
    """Crée un outil MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        tool_id = generate_id('tool')

        # Default schema if not provided
        if input_schema is None:
            input_schema = {"type": "object", "properties": {}, "required": []}

        schema_json = json.dumps(input_schema)

        await conn.execute(
            """INSERT INTO tools (id, server_id, name, description, input_schema, enabled)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
            tool_id, server_id, name, description, schema_json, enabled
        )
        return tool_id

async def get_tool(tool_id: str) -> Optional[Dict]:
    """Récupère un outil MCP par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM tools WHERE id = $1", tool_id)
        return dict(result) if result else None

async def list_tools_by_server(server_id: str) -> List[Dict]:
    """Liste les outils d'un serveur MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM tools WHERE server_id = $1 ORDER BY created_at DESC",
            server_id
        )
        return [dict(row) for row in rows]

async def update_tool(tool_id: str, name: str = None, description: str = None,
                     enabled: bool = None) -> bool:
    """Met à jour un outil MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

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
            return False

        params.append(tool_id)

        query = f"UPDATE tools SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_tool(tool_id: str) -> bool:
    """Supprime un outil MCP."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tools WHERE id = $1", tool_id)
        return int(result.split()[1]) > 0

async def delete_server_tools(server_id: str) -> int:
    """Supprime tous les tools d'un serveur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tools WHERE server_id = $1", server_id)
        return int(result.split()[1])

# ============================
# CONFIGURATIONS
# ============================

async def create_configuration(
    agent_id: str,
    entity_type: str,
    entity_id: str,
    config_data: dict = None,
    enabled: bool = True
) -> str:
    """
    Crée une configuration générique (agent ↔ serveur/ressource).

    Args:
        agent_id: ID de l'agent
        entity_type: Type d'entité ('server' ou 'resource')
        entity_id: ID du serveur ou de la ressource
        config_data: Données de configuration (ex: {"tools": [{"id": "...", "enabled": true}]} pour MCP)
        enabled: Actif ou non
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        config_id = generate_id('configuration')
        config_json = json.dumps(config_data or {})
        await conn.execute(
            """INSERT INTO configurations (id, agent_id, entity_type, entity_id, config_data, enabled)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
            config_id, agent_id, entity_type, entity_id, config_json, enabled
        )
        return config_id

async def get_configuration(config_id: str) -> Optional[Dict]:
    """Récupère une configuration par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM configurations WHERE id = $1", config_id)
        return dict(result) if result else None

async def list_configurations_by_agent(agent_id: str, entity_type: str = None) -> List[Dict]:
    """
    Liste les configurations d'un agent.

    Args:
        agent_id: ID de l'agent
        entity_type: Optionnel - filtre par type ('server', 'resource')
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if entity_type:
            rows = await conn.fetch(
                """SELECT * FROM configurations
                   WHERE agent_id = $1 AND entity_type = $2
                   ORDER BY created_at DESC""",
                agent_id, entity_type
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM configurations WHERE agent_id = $1 ORDER BY created_at DESC",
                agent_id
            )
        return [dict(row) for row in rows]

async def delete_configuration(config_id: str) -> bool:
    """Supprime une configuration."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM configurations WHERE id = $1", config_id)
        return int(result.split()[1]) > 0

async def toggle_configuration(config_id: str, enabled: bool) -> bool:
    """Active/désactive une configuration."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE configurations SET enabled = $1 WHERE id = $2",
            enabled, config_id
        )
        return int(result.split()[1]) > 0

# ============================
# IMPACT ANALYSIS
# ============================

async def get_agents_using_server(server_id: str) -> List[Dict]:
    """
    Récupère tous les agents qui utilisent ce serveur MCP.

    Returns:
        Liste d'agents avec leurs configurations complètes.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT DISTINCT a.id, a.name, a.user_id
               FROM agents a
               JOIN configurations c ON c.agent_id = a.id
               WHERE c.entity_type = 'server' AND c.entity_id = $1""",
            server_id
        )
        return [dict(row) for row in rows]

async def get_server_deletion_impact(server_id: str) -> Dict:
    """
    Calcule l'impact de la suppression d'un serveur MCP.

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
        # Récupérer tous les agents utilisant ce serveur
        agents_using_server = await get_agents_using_server(server_id)

        agents_to_delete = []
        agents_to_update = []
        total_chats = 0

        for agent in agents_using_server:
            agent_id = agent['id']

            # Compter les configurations de cet agent
            config_count = await conn.fetchval(
                "SELECT COUNT(*) FROM configurations WHERE agent_id = $1",
                agent_id
            )

            # Si l'agent n'a qu'une seule config (celle du serveur à supprimer)
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
               WHERE entity_type = 'server' AND entity_id = $1""",
            server_id
        )

        return {
            "agents_to_delete": agents_to_delete,
            "agents_to_update": agents_to_update,
            "chats_to_delete": total_chats,
            "configurations_to_delete": config_count or 0
        }

# ============================
# HELPERS FOR VALIDATION
# ============================

async def get_server_by_name_and_user(name: str, user_id: str) -> Optional[Dict]:
    """
    Récupère un serveur par nom ET user_id (pour vérifier l'unicité).

    Utilisé par les validators pour vérifier qu'un nom n'est pas déjà utilisé
    par le même utilisateur.

    Args:
        name: Nom du serveur
        user_id: ID de l'utilisateur

    Returns:
        Dict du serveur si trouvé, None sinon
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM servers WHERE name = $1 AND user_id = $2",
            name, user_id
        )
        return dict(result) if result else None

async def count_servers_by_user(user_id: str) -> int:
    """
    Compte le nombre de serveurs d'un utilisateur.

    Utilisé pour vérifier le quota (max 100 serveurs par user non-admin).

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Nombre de serveurs
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM servers WHERE user_id = $1",
            user_id
        )
        return count or 0
