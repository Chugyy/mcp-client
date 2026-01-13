# db.py - Gestion de base de données asynchrone

import asyncpg
from pathlib import Path
from config.config import settings
from config.logger import logger

# Global test pool for test mode (set by test fixtures)
_test_pool = None

async def get_pool() -> asyncpg.Pool:
    """Returns the global database connection pool.

    In test mode, returns _test_pool if set.
    Otherwise returns the FastAPI app.state.db_pool.
    """
    if _test_pool is not None:
        return _test_pool

    from app.api.main import app
    return app.state.db_pool

async def get_connection():
    """DEPRECATED: Use get_pool() instead. Kept for backward compatibility during migration."""
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )

    # Configure search_path for schema organization
    # Order: core → agents → chat → mcp → resources → audit
    await conn.execute("""
        SET search_path TO core, agents, chat, mcp, resources, audit, public
    """)

    return conn

async def init_db():
    """Vérifie la connexion à la base de données."""
    conn = await get_connection()
    try:
        await conn.execute("SELECT 1")
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {str(e)}")
        raise
    finally:
        await conn.close()


async def clear_all_data():
    """Vide toutes les données de toutes les tables sans supprimer les tables."""
    conn = await get_connection()
    try:
        # Liste des tables dans l'ordre inverse des dépendances (pour respecter les foreign keys)
        # Format: schema.table
        tables = [
            # Dependent tables first
            'agents.configurations',
            'mcp.tools',
            'chat.messages',
            'audit.validations',
            'agents.memberships',
            'chat.chats',
            'resources.uploads',
            'resources.embeddings',
            'core.reset_tokens',
            'core.user_providers',
            'core.models',
            'core.api_keys',
            'mcp.oauth_tokens',
            'mcp.servers',
            'resources.resources',
            'agents.agents',
            'agents.teams',
            'core.services',
            'core.users',
            'audit.logs',
            'public._migrations'  # Migration tracking table (still in public)
        ]

        # Désactiver temporairement les contraintes de clés étrangères
        await conn.execute("SET session_replication_role = 'replica';")

        deleted_count = 0
        for table in tables:
            try:
                result = await conn.execute(f"DELETE FROM {table}")
                # Extraire le nombre de lignes supprimées du résultat
                count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                deleted_count += count
                logger.info(f"✅ Table '{table}' vidée ({count} lignes supprimées)")
            except Exception as e:
                # Si la table n'existe pas, continuer
                if 'does not exist' in str(e):
                    logger.debug(f"⚠️ Table '{table}' inexistante (ignoré)")
                else:
                    logger.warning(f"⚠️ Erreur lors du vidage de '{table}': {e}")

        # Réactiver les contraintes de clés étrangères
        await conn.execute("SET session_replication_role = 'origin';")

        logger.info(f"✅ Toutes les données ont été supprimées ({deleted_count} lignes au total)")

    except Exception as e:
        logger.error(f"❌ Erreur lors du vidage des données: {e}")
        raise
    finally:
        await conn.close()
