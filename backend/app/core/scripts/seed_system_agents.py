#!/usr/bin/env python3
"""
DEPRECATED: Ce script est obsolète.
Les agents système sont maintenant définis dans app.core.system.definitions.agents
et synchronisés automatiquement au démarrage.

Conserver uniquement pour référence.

Script de seed pour les agents système.
Crée l'utilisateur système et les agents système (notamment le Builder).
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Ajouter le dossier racine du backend au PYTHONPATH
backend_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.database import crud
from config.logger import logger

# ============================
# CONSTANTES
# ============================

SYSTEM_USER = {
    "id": "__system__",
    "email": "system@internal",
    "name": "System User",
    "password": "N/A"  # Non utilisable pour login
}

SYSTEM_AGENTS = [
    {
        "id": "__system_builder_automation__",
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
- Proposer des améliorations si tu identifies des optimisations possibles

**EXEMPLE DE CONVERSATION :**

User: "Je veux créer une automation qui envoie un email chaque matin à 9h avec le résumé des tâches du jour"

Toi: "Parfait ! Je vais créer cette automation pour toi. Voici ce que je vais faire :

1. Créer une automation appelée 'Daily Task Summary Email'
2. Ajouter une étape pour récupérer les tâches du jour
3. Ajouter une étape pour formater l'email
4. Ajouter une étape pour envoyer l'email
5. Configurer un trigger temporel à 9h chaque jour
6. Tester l'automation

Est-ce que cela correspond à ce que tu veux ?"

Sois toujours clair, précis et pédagogue dans tes explications.""",
        "tags": ["automation", "builder", "system"],
        "is_system": True,
        "enabled": True
    }
]

# ============================
# FONCTIONS
# ============================

async def seed_system_user(force: bool = False):
    """
    Crée l'utilisateur système s'il n'existe pas.

    Args:
        force: Si True, recrée l'utilisateur même s'il existe déjà
    """
    try:
        # Vérifier si l'utilisateur système existe
        existing_user = await crud.get_user(SYSTEM_USER["id"])

        if existing_user:
            if force:
                logger.warning(f"⚠️  L'utilisateur système existe déjà (id={SYSTEM_USER['id']})")
                logger.warning("   Option --force ignorée pour l'utilisateur système (trop risqué)")
                return
            else:
                logger.info(f"✅ L'utilisateur système existe déjà (id={SYSTEM_USER['id']})")
                return

        # Créer l'utilisateur système avec un ID fixe
        # Note: On doit insérer directement car l'ID est fixe
        from app.database.db import get_connection
        conn = await get_connection()
        try:
            await conn.execute(
                """INSERT INTO core.users (id, email, password, name, preferences)
                   VALUES ($1, $2, $3, $4, $5::jsonb)""",
                SYSTEM_USER["id"],
                SYSTEM_USER["email"],
                SYSTEM_USER["password"],
                SYSTEM_USER["name"],
                '{"theme": "system", "language": "en"}'
            )
            logger.info(f"✅ Utilisateur système créé : {SYSTEM_USER['id']}")
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de l'utilisateur système : {e}")
        raise


async def seed_system_agents(force: bool = False):
    """
    Crée les agents système s'ils n'existent pas.

    Args:
        force: Si True, recrée les agents même s'ils existent déjà
    """
    created_count = 0
    skipped_count = 0

    for agent_data in SYSTEM_AGENTS:
        try:
            # Vérifier si l'agent existe déjà
            existing_agent = await crud.get_agent(agent_data["id"])

            if existing_agent:
                if force:
                    logger.info(f"🔄 Suppression et recréation de l'agent : {agent_data['name']}")
                    await crud.delete_agent(agent_data["id"])
                else:
                    logger.info(f"⏭️  Agent système déjà existant (ignoré) : {agent_data['name']}")
                    skipped_count += 1
                    continue

            # Créer l'agent système avec un ID fixe
            from app.database.db import get_connection
            conn = await get_connection()
            try:
                await conn.execute(
                    """INSERT INTO agents.agents (id, user_id, name, description, system_prompt, tags, is_system, enabled)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                    agent_data["id"],
                    SYSTEM_USER["id"],
                    agent_data["name"],
                    agent_data["description"],
                    agent_data["system_prompt"],
                    agent_data["tags"],
                    agent_data["is_system"],
                    agent_data["enabled"]
                )
                logger.info(f"✅ Agent système créé : {agent_data['name']} (id={agent_data['id']})")
                created_count += 1
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"❌ Erreur lors de la création de l'agent {agent_data['name']} : {e}")
            raise

    # Résumé
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"📊 RÉSUMÉ DU SEED DES AGENTS SYSTÈME")
    logger.info("=" * 60)
    logger.info(f"   Agents créés   : {created_count}")
    logger.info(f"   Agents ignorés : {skipped_count}")
    logger.info(f"   Total          : {len(SYSTEM_AGENTS)}")
    logger.info("=" * 60)


async def main(force: bool = False):
    """
    Fonction principale : orchestre le seed.

    Args:
        force: Si True, recrée les entités même si elles existent déjà
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("🚀 SEED DES AGENTS SYSTÈME")
    logger.info("=" * 60)
    logger.info("")

    try:
        # 1. Créer l'utilisateur système
        logger.info("📍 Étape 1/2 : Création de l'utilisateur système")
        await seed_system_user(force)
        logger.info("")

        # 2. Créer les agents système
        logger.info("📍 Étape 2/2 : Création des agents système")
        await seed_system_agents(force)
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
        description="Seed des agents système (Builder, etc.)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recréer les agents même s'ils existent déjà (attention : supprime les agents existants)"
    )

    args = parser.parse_args()

    asyncio.run(main(force=args.force))
