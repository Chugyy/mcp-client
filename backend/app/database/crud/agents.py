import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# AGENTS
# ============================

async def create_agent(user_id: str, name: str, system_prompt: str,
                      description: str = None, tags: List[str] = None,
                      enabled: bool = True, is_system: bool = False) -> str:
    """Crée un agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        agent_id = generate_id('agent')
        await conn.execute(
            """INSERT INTO agents (id, user_id, name, description, system_prompt,
               tags, enabled, is_system)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            agent_id, user_id, name, description, system_prompt,
            tags or [], enabled, is_system
        )
        return agent_id

async def get_agent(agent_id: str) -> Optional[Dict]:
    """Récupère un agent par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
        return dict(result) if result else None

async def get_agent_by_name(name: str) -> Optional[Dict]:
    """Récupère un agent par son nom."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM agents WHERE name = $1", name)
        return dict(result) if result else None

async def list_agents_by_user(user_id: str) -> List[Dict]:
    """Liste tous les agents d'un utilisateur + agents publics internes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM agents
               WHERE user_id = $1 OR (user_id = '__internal__' AND is_public = true)
               ORDER BY user_id = '__internal__' DESC, created_at DESC""",
            user_id
        )
        return [dict(row) for row in rows]

async def update_agent(agent_id: str, name: str = None, description: str = None,
                      system_prompt: str = None, tags: List[str] = None,
                      enabled: bool = None) -> bool:
    """Met à jour un agent."""
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

        if system_prompt is not None:
            updates.append(f"system_prompt = ${param_count}")
            params.append(system_prompt)
            param_count += 1

        if tags is not None:
            updates.append(f"tags = ${param_count}")
            params.append(tags)
            param_count += 1

        if enabled is not None:
            updates.append(f"enabled = ${param_count}")
            params.append(enabled)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(agent_id)

        query = f"UPDATE agents SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_agent(agent_id: str) -> bool:
    """Supprime un agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
        return int(result.split()[1]) > 0

async def duplicate_agent(agent_id: str, user_id: str) -> Optional[str]:
    """Duplique un agent existant avec ses configurations MCP et ressources."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer l'agent source
        source_agent = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
        if not source_agent:
            return None

        # Vérifier que l'agent appartient à l'utilisateur (sauf agents système)
        if source_agent['user_id'] != user_id and not source_agent['is_system']:
            return None

        # Générer un nouveau nom unique
        base_name = source_agent['name']
        new_name = f"{base_name} (copie)"

        # Vérifier si le nom existe déjà et incrémenter si nécessaire
        counter = 1
        while await conn.fetchrow("SELECT id FROM agents WHERE name = $1 AND user_id = $2", new_name, user_id):
            counter += 1
            new_name = f"{base_name} (copie {counter})"

        # Créer le nouvel agent
        new_agent_id = generate_id('agent')
        await conn.execute(
            """INSERT INTO agents (id, user_id, name, description, system_prompt,
               tags, enabled, is_system)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            new_agent_id, user_id, new_name, source_agent['description'],
            source_agent['system_prompt'], source_agent['tags'],
            source_agent['enabled'], False  # Les duplications ne sont jamais système
        )

        # Dupliquer les configurations (MCP servers et ressources)
        source_configs = await conn.fetch(
            "SELECT entity_type, entity_id, config_data, enabled FROM configurations WHERE agent_id = $1",
            agent_id
        )
        for config in source_configs:
            config_id = generate_id('configuration')
            await conn.execute(
                """INSERT INTO configurations (id, agent_id, entity_type, entity_id, config_data, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                config_id, new_agent_id, config['entity_type'], config['entity_id'],
                config['config_data'], config['enabled']
            )

        # Dupliquer l'avatar si existant
        source_avatar = await conn.fetchrow(
            "SELECT * FROM uploads WHERE agent_id = $1 AND type = 'avatar'",
            agent_id
        )
        if source_avatar:
            # Importer les fonctions nécessaires pour copier l'avatar
            from app.database.crud import uploads as crud_uploads
            import shutil
            import os

            # Copier le fichier physique
            source_path = source_avatar['file_path']
            if os.path.exists(source_path):
                # Générer le nouveau chemin
                file_extension = os.path.splitext(source_avatar['filename'])[1]
                new_filename = f"{new_agent_id}_avatar{file_extension}"
                uploads_dir = os.path.dirname(source_path)
                new_path = os.path.join(uploads_dir, new_filename)

                # Copier le fichier
                shutil.copy2(source_path, new_path)

                # Créer l'entrée dans la table uploads
                upload_id = generate_id('upload')
                await conn.execute(
                    """INSERT INTO uploads (id, user_id, agent_id, type, filename, file_path, file_size, mime_type)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                    upload_id, user_id, new_agent_id, 'avatar', new_filename, new_path,
                    source_avatar['file_size'], source_avatar['mime_type']
                )

        return new_agent_id


async def get_agent_by_name_and_user(name: str, user_id: str) -> Optional[Dict]:
    """
    Récupère un agent par son nom et son utilisateur.

    Utilisé pour vérifier l'unicité des noms d'agents.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM agents WHERE name = $1 AND user_id = $2",
            name, user_id
        )
        return dict(result) if result else None


async def count_agents_by_user(user_id: str) -> int:
    """
    Compte le nombre d'agents d'un utilisateur.

    Utilisé pour vérifier le quota d'agents.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM agents WHERE user_id = $1",
            user_id
        )
        return count or 0
