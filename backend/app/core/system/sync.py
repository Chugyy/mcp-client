"""
Synchronisation de toute l'infrastructure système.
Source de vérité unique : définitions Python → BDD.
"""

import hashlib
import json
from typing import List, Dict, Any
from config.logger import logger
from app.database.db import get_connection
from app.core.system.definitions import (
    INTERNAL_USER,
    INTERNAL_SERVERS,
    SYSTEM_AGENTS,
    SYSTEM_RESOURCES,
    AUTOMATION_TOOLS,
    RAG_TOOLS,
    DISCOVERY_TOOLS,
    SYSTEM_SERVICES
)


async def sync_internal_infrastructure():
    """
    Point d'entrée principal : synchronise TOUTE l'infrastructure système.

    Ordre d'exécution (respecte les dépendances) :
    1. User __internal__
    2. Services LLM (OpenAI, Anthropic)
    3. Serveurs MCP internes
    4. Tools internes
    5. Agents système
    6. Ressources système
    """
    logger.info("🔄 Synchronisation de l'infrastructure système...")

    try:
        await _ensure_internal_user()
        await _sync_services()
        await _sync_servers()
        await _sync_tools()
        await _sync_agents()
        await _sync_resources()

        logger.info("✅ Infrastructure système synchronisée")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la sync infrastructure : {e}")
        raise


async def _ensure_internal_user():
    """Crée l'utilisateur __internal__ s'il n'existe pas."""
    conn = await get_connection()
    try:
        existing = await conn.fetchrow(
            "SELECT id FROM core.users WHERE id = $1",
            INTERNAL_USER["id"]
        )

        if existing:
            logger.info(f"✅ Utilisateur interne existe : {INTERNAL_USER['id']}")
            return

        await conn.execute(
            """INSERT INTO core.users (id, email, password, name, preferences, is_system)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
            INTERNAL_USER["id"],
            INTERNAL_USER["email"],
            INTERNAL_USER["password"],
            INTERNAL_USER["name"],
            '{"theme": "system", "language": "en"}',
            INTERNAL_USER["is_system"]
        )
        logger.info(f"✅ Utilisateur interne créé : {INTERNAL_USER['id']}")

    finally:
        await conn.close()


async def _sync_services():
    """Synchronise les services LLM système (OpenAI, Anthropic)."""
    services_hash = _hash_data(SYSTEM_SERVICES)
    stored_hash = await _get_stored_hash("system_services")

    if services_hash == stored_hash:
        logger.info("✅ Services LLM à jour")
        return

    logger.info(f"🔄 Synchronisation des services LLM...")

    conn = await get_connection()
    try:
        for service in SYSTEM_SERVICES:
            await conn.execute(
                """INSERT INTO core.services (id, name, provider, description, status)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (id) DO UPDATE SET
                       name = EXCLUDED.name,
                       description = EXCLUDED.description,
                       status = EXCLUDED.status,
                       updated_at = NOW()""",
                service["id"],
                service["name"],
                service["provider"],
                service["description"],
                service["status"]
            )

        await _save_hash("system_services", services_hash)
        logger.info(f"✅ {len(SYSTEM_SERVICES)} service(s) LLM synchronisé(s)")

    finally:
        await conn.close()


async def _sync_servers():
    """Synchronise les serveurs MCP internes."""
    servers_hash = _hash_data(INTERNAL_SERVERS)
    stored_hash = await _get_stored_hash("internal_servers")

    if servers_hash == stored_hash:
        logger.info("✅ Serveurs internes à jour")
        return

    logger.info(f"🔄 Synchronisation des serveurs internes...")

    conn = await get_connection()
    try:
        for server in INTERNAL_SERVERS:
            await conn.execute(
                """INSERT INTO mcp.servers (id, user_id, name, description, url, auth_type, is_system, is_public, status, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                   ON CONFLICT (id) DO UPDATE SET
                       name = EXCLUDED.name,
                       description = EXCLUDED.description,
                       url = EXCLUDED.url,
                       updated_at = NOW()""",
                server["id"],
                server["user_id"],
                server["name"],
                server["description"],
                server["url"],
                server["auth_type"],
                server["is_system"],
                server["is_public"],
                server["status"],
                server["enabled"]
            )

        await _save_hash("internal_servers", servers_hash)
        logger.info(f"✅ {len(INTERNAL_SERVERS)} serveur(s) synchronisé(s)")

    finally:
        await conn.close()


async def _sync_tools():
    """
    Synchronise les tools internes sur leurs serveurs respectifs.
    - RAG_TOOLS → srv_internal_rag
    - AUTOMATION_TOOLS + DISCOVERY_TOOLS → srv_internal_automation
    """
    # Mapping serveur → tools
    tools_mapping = {
        "srv_internal_rag": list(RAG_TOOLS),
        "srv_internal_automation": list(AUTOMATION_TOOLS) + list(DISCOVERY_TOOLS)
    }

    all_tools = list(AUTOMATION_TOOLS) + list(RAG_TOOLS) + list(DISCOVERY_TOOLS)

    # Calculer hash des tools
    tools_hash = _hash_data([
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
            "is_default": t.is_default,
            "is_removable": t.is_removable
        }
        for t in all_tools
    ])

    stored_hash = await _get_stored_hash("internal_tools")

    if tools_hash == stored_hash:
        logger.info("✅ Tools internes à jour")
        return

    logger.info(f"🔄 Synchronisation des tools internes...")

    conn = await get_connection()
    try:
        # 1. DELETE tools des serveurs système
        server_ids = [s["id"] for s in INTERNAL_SERVERS]
        for server_id in server_ids:
            await conn.execute(
                "DELETE FROM mcp.tools WHERE server_id = $1",
                server_id
            )

        # 2. INSERT tools sur leurs serveurs respectifs
        total_synced = 0
        for server_id, tools in tools_mapping.items():
            for tool in tools:
                await conn.execute(
                    """INSERT INTO mcp.tools (server_id, name, description, input_schema, is_default, is_removable, enabled)
                       VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)""",
                    server_id,
                    tool.name,
                    tool.description,
                    json.dumps(tool.input_schema),
                    tool.is_default,
                    tool.is_removable,
                    True
                )
                total_synced += 1

            logger.info(f"  ✅ {server_id}: {len(tools)} tool(s)")

        await _save_hash("internal_tools", tools_hash)
        logger.info(f"✅ Total: {total_synced} tool(s) synchronisé(s)")

    finally:
        await conn.close()


async def _sync_agents():
    """Synchronise les agents système."""
    agents_hash = _hash_data(SYSTEM_AGENTS)
    stored_hash = await _get_stored_hash("system_agents")

    if agents_hash == stored_hash:
        logger.info("✅ Agents système à jour")
        return

    logger.info(f"🔄 Synchronisation des agents système...")

    conn = await get_connection()
    try:
        for agent in SYSTEM_AGENTS:
            # UPSERT agent
            await conn.execute(
                """INSERT INTO agents.agents (id, user_id, name, description, system_prompt, tags, is_system, is_public, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   ON CONFLICT (id) DO UPDATE SET
                       name = EXCLUDED.name,
                       description = EXCLUDED.description,
                       system_prompt = EXCLUDED.system_prompt,
                       tags = EXCLUDED.tags,
                       is_public = EXCLUDED.is_public,
                       enabled = EXCLUDED.enabled,
                       updated_at = NOW()""",
                agent["id"],
                agent["user_id"],
                agent["name"],
                agent["description"],
                agent["system_prompt"],
                agent["tags"],
                agent["is_system"],
                agent["is_public"],
                agent["enabled"]
            )

            # Sync configurations (serveurs MCP attachés)
            await conn.execute(
                "DELETE FROM agents.configurations WHERE agent_id = $1 AND entity_type = 'server'",
                agent["id"]
            )

            for server_id in agent.get("server_ids", []):
                from app.core.utils.id_generator import generate_id
                config_id = generate_id('configuration')

                await conn.execute(
                    """INSERT INTO agents.configurations (id, agent_id, entity_type, entity_id, config_data, enabled)
                       VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
                    config_id,
                    agent["id"],
                    'server',
                    server_id,
                    '{}',
                    True
                )

        await _save_hash("system_agents", agents_hash)
        logger.info(f"✅ {len(SYSTEM_AGENTS)} agent(s) système synchronisé(s)")

    finally:
        await conn.close()


async def _sync_resources():
    """Synchronise les ressources système (future implémentation)."""
    if not SYSTEM_RESOURCES:
        logger.debug("ℹ️  Aucune ressource système à synchroniser")
        return

    # TODO: Implémenter quand des ressources système seront définies
    logger.info("⏭️  Sync ressources système non implémenté (SYSTEM_RESOURCES vide)")


def _hash_data(data: Any) -> str:
    """Calcule un hash SHA256 des données."""
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()


async def _get_stored_hash(key: str) -> str:
    """Récupère un hash stocké en BDD."""
    conn = await get_connection()
    try:
        await conn.execute("CREATE SCHEMA IF NOT EXISTS system")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system.sync_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        row = await conn.fetchrow(
            "SELECT value FROM system.sync_state WHERE key = $1",
            key
        )

        return row['value'] if row else ""

    finally:
        await conn.close()


async def _save_hash(key: str, hash_value: str):
    """Sauvegarde un hash en BDD."""
    conn = await get_connection()
    try:
        await conn.execute("""
            INSERT INTO system.sync_state (key, value, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()
        """, key, hash_value)
    finally:
        await conn.close()
