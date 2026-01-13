#!/usr/bin/env python3
"""
DEPRECATED: Ce script est obsolète.
L'infrastructure système est maintenant synchronisée automatiquement
au démarrage de l'application via app.core.system.sync.

Conserver uniquement pour référence ou reset complet en dev.

Script de seed pour l'infrastructure interne.
Crée l'utilisateur __internal__, les serveurs MCP internes, les tools et l'agent Builder.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Ajouter le dossier racine du backend au PYTHONPATH
backend_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.database import crud
from app.database.db import get_connection
from config.logger import logger
from config.config import settings

# ============================
# CONSTANTES
# ============================

INTERNAL_USER = {
    "id": "__internal__",
    "email": "internal@system",
    "name": "Internal System",
    "password": "N/A"  # Non utilisable pour login
}

# Définition du serveur MCP privé (automation)
INTERNAL_PRIVATE_SERVER = {
    "id": "srv_internal_private",
    "name": "Internal Automation Tools",
    "description": "Internal MCP server for automation tools (private access only)",
    "url": settings.internal_mcp_url,
    "user_id": "__internal__",
    "is_public": False,
    "is_system": True,
    "status": "active"
}

# Définition du serveur MCP public (utilities)
INTERNAL_PUBLIC_SERVER = {
    "id": "srv_internal_public",
    "name": "Internal Utility Tools",
    "description": "Internal MCP server with public utility tools",
    "url": settings.internal_mcp_url,
    "user_id": "__internal__",
    "is_public": True,
    "is_system": True,
    "status": "active"
}

# Tools du serveur PRIVÉ (automation)
# IMPORTANT: Les tools sont maintenant définis dans automation.py (source unique de vérité)
# et synchronisés automatiquement au démarrage de l'app via sync_internal_tools()
from app.core.system.definitions.tools.automation import AUTOMATION_TOOLS

# Convertir AUTOMATION_TOOLS (ToolDefinition) en format dict pour le seed
PRIVATE_TOOLS = [
    {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
        "is_default": False,
        "is_removable": False  # Tools internes ne sont pas removables
    }
    for tool in AUTOMATION_TOOLS
]

# Tools du serveur PUBLIC (utilities)
PUBLIC_TOOLS = [
    {
        "name": "translate_text",
        "description": "Translate text from one language to another (example tool)",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate"},
                "source_lang": {"type": "string", "description": "Source language code"},
                "target_lang": {"type": "string", "description": "Target language code"}
            },
            "required": ["text", "source_lang", "target_lang"]
        },
        "is_default": False,
        "is_removable": True
    },
    {
        "name": "summarize_document",
        "description": "Summarize a document (example tool)",
        "input_schema": {
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document to summarize"},
                "max_length": {"type": "integer", "description": "Maximum summary length", "default": 200}
            },
            "required": ["document"]
        },
        "is_default": False,
        "is_removable": True
    }
]

# Tools DEFAULT (attachés automatiquement à tous les agents)
# IMPORTANT: Les tools RAG sont maintenant définis dans resources/tools.py (source unique de vérité)
# et synchronisés automatiquement au démarrage de l'app via sync_internal_tools()
from app.core.system.definitions.tools.rag import RAG_TOOLS

# Convertir RAG_TOOLS (ToolDefinition) en format dict pour le seed
DEFAULT_TOOLS = [
    {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
        "is_default": True,   # RAG tools sont auto-attachés à tous les agents
        "is_removable": False # RAG tools ne sont pas removables
    }
    for tool in RAG_TOOLS
]

# Agent Builder
BUILDER_AGENT = {
    "id": "__internal_builder__",
    "name": "Automation Builder",
    "description": "AI agent specialized in building and validating automation workflows. Can create automations, add workflow steps, configure triggers, and test workflows.",
    "system_prompt": """Tu es un expert en création d'automations et de workflows intelligents.

**TES CAPACITÉS :**

Tu as accès aux outils suivants pour construire des automations :
- `create_automation` : Créer une nouvelle automation
- `add_workflow_step` : Ajouter une étape au workflow
- `add_trigger` : Configurer un déclencheur pour l'automation
- `test_automation` : Tester une automation avant de la déployer

**TON WORKFLOW DE CRÉATION :**

1. **Comprendre le besoin** : Poser des questions pour bien comprendre l'objectif de l'automation
2. **Créer l'automation** : Utiliser `create_automation` avec un nom et une description claire
3. **Ajouter les steps** : Utiliser `add_workflow_step` pour chaque étape, une par une
4. **Configurer le trigger** : Utiliser `add_trigger` pour définir quand l'automation se déclenche
5. **Tester** : Utiliser `test_automation` pour vérifier que tout fonctionne correctement

**TES PRINCIPES :**

- Toujours expliquer ce que tu fais à chaque étape
- Demander confirmation avant de créer ou modifier une automation
- Construire des workflows simples et maintenables
- Tester avant de finaliser
- Proposer des améliorations si tu identifies des optimisations possibles""",
    "tags": ["automation", "builder", "internal"],
    "is_system": True,
    "is_public": True,
    "enabled": True,
    "tool_ids": []  # Les tools seront attachés après création
}

# ============================
# FONCTIONS
# ============================

async def seed_internal_user(force: bool = False):
    """Crée l'utilisateur __internal__ s'il n'existe pas."""
    try:
        existing_user = await crud.get_user(INTERNAL_USER["id"])

        if existing_user:
            logger.info(f"✅ L'utilisateur interne existe déjà (id={INTERNAL_USER['id']})")
            return

        # Créer l'utilisateur interne
        conn = await get_connection()
        try:
            await conn.execute(
                """INSERT INTO core.users (id, email, password, name, preferences, is_system)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
                INTERNAL_USER["id"],
                INTERNAL_USER["email"],
                INTERNAL_USER["password"],
                INTERNAL_USER["name"],
                '{"theme": "system", "language": "en"}',
                True
            )
            logger.info(f"✅ Utilisateur interne créé : {INTERNAL_USER['id']}")
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de l'utilisateur interne : {e}")
        raise


async def seed_internal_mcp_server(force: bool = False):
    """Crée le serveur MCP privé (automation)."""
    try:
        conn = await get_connection()
        try:
            # Vérifier si le serveur existe
            existing = await conn.fetchrow(
                "SELECT id FROM mcp.servers WHERE id = $1",
                INTERNAL_PRIVATE_SERVER["id"]
            )

            if existing:
                if force:
                    logger.info(f"🔄 Suppression et recréation du serveur privé")
                    await conn.execute("DELETE FROM mcp.servers WHERE id = $1", INTERNAL_PRIVATE_SERVER["id"])
                else:
                    logger.info(f"✅ Serveur MCP privé existe déjà (id={INTERNAL_PRIVATE_SERVER['id']})")
                    return INTERNAL_PRIVATE_SERVER["id"]

            # Créer le serveur
            await conn.execute(
                """INSERT INTO mcp.servers (id, user_id, name, description, url, auth_type, is_public, is_system, status, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                INTERNAL_PRIVATE_SERVER["id"],
                INTERNAL_PRIVATE_SERVER["user_id"],
                INTERNAL_PRIVATE_SERVER["name"],
                INTERNAL_PRIVATE_SERVER["description"],
                INTERNAL_PRIVATE_SERVER["url"],
                'none',
                INTERNAL_PRIVATE_SERVER["is_public"],
                INTERNAL_PRIVATE_SERVER["is_system"],
                INTERNAL_PRIVATE_SERVER["status"],
                True
            )
            logger.info(f"✅ Serveur MCP privé créé : {INTERNAL_PRIVATE_SERVER['name']}")
            return INTERNAL_PRIVATE_SERVER["id"]

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création du serveur MCP privé : {e}")
        raise


async def seed_public_mcp_server(force: bool = False):
    """Crée le serveur MCP public (utilities)."""
    try:
        conn = await get_connection()
        try:
            # Vérifier si le serveur existe
            existing = await conn.fetchrow(
                "SELECT id FROM mcp.servers WHERE id = $1",
                INTERNAL_PUBLIC_SERVER["id"]
            )

            if existing:
                if force:
                    logger.info(f"🔄 Suppression et recréation du serveur public")
                    await conn.execute("DELETE FROM mcp.servers WHERE id = $1", INTERNAL_PUBLIC_SERVER["id"])
                else:
                    logger.info(f"✅ Serveur MCP public existe déjà (id={INTERNAL_PUBLIC_SERVER['id']})")
                    return INTERNAL_PUBLIC_SERVER["id"]

            # Créer le serveur
            await conn.execute(
                """INSERT INTO mcp.servers (id, user_id, name, description, url, auth_type, is_public, is_system, status, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                INTERNAL_PUBLIC_SERVER["id"],
                INTERNAL_PUBLIC_SERVER["user_id"],
                INTERNAL_PUBLIC_SERVER["name"],
                INTERNAL_PUBLIC_SERVER["description"],
                INTERNAL_PUBLIC_SERVER["url"],
                'none',
                INTERNAL_PUBLIC_SERVER["is_public"],
                INTERNAL_PUBLIC_SERVER["is_system"],
                INTERNAL_PUBLIC_SERVER["status"],
                True
            )
            logger.info(f"✅ Serveur MCP public créé : {INTERNAL_PUBLIC_SERVER['name']}")
            return INTERNAL_PUBLIC_SERVER["id"]

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création du serveur MCP public : {e}")
        raise


async def seed_tools(server_id: str, tools: list, tool_type: str, force: bool = False):
    """Crée les tools pour un serveur donné."""
    try:
        conn = await get_connection()
        try:
            created_count = 0
            skipped_count = 0

            for tool_data in tools:
                # Vérifier si le tool existe
                existing = await conn.fetchrow(
                    "SELECT id FROM mcp.tools WHERE server_id = $1 AND name = $2",
                    server_id, tool_data["name"]
                )

                if existing:
                    if force:
                        await conn.execute(
                            "DELETE FROM mcp.tools WHERE server_id = $1 AND name = $2",
                            server_id, tool_data["name"]
                        )
                    else:
                        logger.info(f"  ⏭️  Tool déjà existant : {tool_data['name']}")
                        skipped_count += 1
                        continue

                # Créer le tool
                import json
                await conn.execute(
                    """INSERT INTO mcp.tools (server_id, name, description, input_schema, is_default, is_removable)
                       VALUES ($1, $2, $3, $4::jsonb, $5, $6)""",
                    server_id,
                    tool_data["name"],
                    tool_data["description"],
                    json.dumps(tool_data["input_schema"]),
                    tool_data["is_default"],
                    tool_data["is_removable"]
                )
                logger.info(f"  ✅ Tool créé : {tool_data['name']}")
                created_count += 1

            logger.info(f"  📊 Tools {tool_type} : {created_count} créés, {skipped_count} ignorés")

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tools {tool_type} : {e}")
        raise


async def seed_builder_agent(private_server_id: str, force: bool = False):
    """Crée l'agent Builder avec les tools d'automation."""
    try:
        conn = await get_connection()
        try:
            # Vérifier si l'agent existe
            existing = await conn.fetchrow(
                "SELECT id FROM agents.agents WHERE id = $1",
                BUILDER_AGENT["id"]
            )

            if existing:
                if force:
                    logger.info(f"🔄 Suppression et recréation de l'agent Builder")
                    # Delete configurations first
                    await conn.execute("DELETE FROM agents.configurations WHERE agent_id = $1", BUILDER_AGENT["id"])
                    await conn.execute("DELETE FROM agents.agents WHERE id = $1", BUILDER_AGENT["id"])
                else:
                    logger.info(f"✅ Agent Builder existe déjà (id={BUILDER_AGENT['id']})")
                    return

            # Créer l'agent
            await conn.execute(
                """INSERT INTO agents.agents (id, user_id, name, description, system_prompt, tags, is_system, is_public, enabled)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                BUILDER_AGENT["id"],
                INTERNAL_USER["id"],
                BUILDER_AGENT["name"],
                BUILDER_AGENT["description"],
                BUILDER_AGENT["system_prompt"],
                BUILDER_AGENT["tags"],
                BUILDER_AGENT["is_system"],
                BUILDER_AGENT["is_public"],
                BUILDER_AGENT["enabled"]
            )

            # Créer la configuration pour lier le serveur MCP privé à l'agent
            # Les tools seront automatiquement associés via le serveur
            from app.core.utils.id_generator import generate_id
            config_id = generate_id('configuration')
            await conn.execute(
                """INSERT INTO agents.configurations (id, agent_id, entity_type, entity_id, config_data, enabled)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
                config_id,
                BUILDER_AGENT["id"],
                'server',
                private_server_id,
                '{}',
                True
            )

            logger.info(f"✅ Agent Builder créé : {BUILDER_AGENT['name']} (lié au serveur {private_server_id})")

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de l'agent Builder : {e}")
        raise


async def main(force: bool = False):
    """Fonction principale : orchestre le seed."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🚀 SEED DE L'INFRASTRUCTURE INTERNE")
    logger.info("=" * 60)
    logger.info("")

    try:
        # 1. Créer l'utilisateur __internal__
        logger.info("📍 Étape 1/6 : Création de l'utilisateur interne")
        await seed_internal_user(force)
        logger.info("")

        # 2. Créer le serveur MCP privé (automation)
        logger.info("📍 Étape 2/6 : Création du serveur MCP privé (automation)")
        private_server_id = await seed_internal_mcp_server(force)
        logger.info("")

        # 3. Créer le serveur MCP public (utilities)
        logger.info("📍 Étape 3/6 : Création du serveur MCP public (utilities)")
        public_server_id = await seed_public_mcp_server(force)
        logger.info("")

        # 4. Créer les tools du serveur privé
        logger.info("📍 Étape 4/6 : Création des tools du serveur privé")
        await seed_tools(private_server_id, PRIVATE_TOOLS, "privés", force)
        logger.info("")

        # 5. Créer les tools du serveur public + tools DEFAULT
        logger.info("📍 Étape 5/6 : Création des tools du serveur public + DEFAULT")
        await seed_tools(public_server_id, PUBLIC_TOOLS + DEFAULT_TOOLS, "publics", force)
        logger.info("")

        # 6. Créer l'agent Builder
        logger.info("📍 Étape 6/6 : Création de l'agent Builder")
        await seed_builder_agent(private_server_id, force)
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ SEED TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 60)
        logger.info("")

    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ ERREUR LORS DU SEED")
        logger.error("=" * 60)
        logger.error(f"Détails : {e}")
        logger.error("")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed de l'infrastructure interne (serveurs MCP, tools, agent Builder)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recréer les entités même si elles existent déjà"
    )

    args = parser.parse_args()

    asyncio.run(main(force=args.force))
