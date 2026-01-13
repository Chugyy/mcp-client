#!/usr/bin/env python3
"""
Script pour initialiser la base de données PostgreSQL locale.

Usage:
    python scripts/init_database.py
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import settings
from app.database.db import init_db

async def check_database_exists():
    """Vérifie si la base de données existe."""
    try:
        # Connexion à la base postgres par défaut pour vérifier l'existence de notre DB
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            database='postgres',
            user=settings.db_user,
            password=settings.db_password
        )

        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.db_name
        )

        await conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Error checking database existence: {e}")
        return False

async def create_database():
    """Crée la base de données si elle n'existe pas."""
    try:
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            database='postgres',
            user=settings.db_user,
            password=settings.db_password
        )

        # CREATE DATABASE ne peut pas être dans une transaction
        await conn.execute(f'CREATE DATABASE {settings.db_name}')
        print(f"✅ Database '{settings.db_name}' created successfully")

        await conn.close()
    except asyncpg.exceptions.DuplicateDatabaseError:
        print(f"ℹ️  Database '{settings.db_name}' already exists")
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise

async def main():
    """Fonction principale."""
    print("=" * 60)
    print("🚀 PostgreSQL Database Initialization")
    print("=" * 60)
    print()

    # Étape 1: Vérifier/Créer la base de données
    print("📋 Step 1: Checking database existence...")
    db_exists = await check_database_exists()

    if not db_exists:
        print(f"📦 Creating database '{settings.db_name}'...")
        await create_database()
    else:
        print(f"✅ Database '{settings.db_name}' already exists")

    print()

    # Étape 2: Exécuter les migrations
    print("📋 Step 2: Running migrations...")
    try:
        await init_db()
        print("✅ Migrations executed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("🎉 Database initialization completed successfully!")
    print("=" * 60)
    print()
    print(f"Database: {settings.db_name}")
    print(f"Host: {settings.db_host}:{settings.db_port}")
    print(f"User: {settings.db_user}")

if __name__ == "__main__":
    asyncio.run(main())
