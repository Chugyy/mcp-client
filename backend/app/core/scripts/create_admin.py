#!/usr/bin/env python3
"""
Script pour créer un utilisateur admin en base de données.
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le dossier racine du backend au PYTHONPATH
backend_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.database import crud
from app.core.utils.auth import hash_password

async def create_admin():
    """Crée un utilisateur admin."""
    email = "admin@admin.admin"
    password = "adminadmin"
    name = "Administrator"

    print("🔐 Creating admin user...")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print()

    # Vérifier si l'utilisateur existe déjà
    existing_user = await crud.get_user_by_email(email)
    if existing_user:
        print(f"⚠️  User with email '{email}' already exists!")
        print(f"User ID: {existing_user['id']}")
        return

    # Hasher le mot de passe
    password_hash = hash_password(password)

    # Créer l'utilisateur
    try:
        user_id = await crud.create_user(
            email=email,
            password=password_hash,
            name=name
        )

        print(f"✅ Admin user created successfully!")
        print(f"User ID: {user_id}")
        print(f"Email: {email}")
        print(f"Name: {name}")
        print()
        print("You can now login with:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")

    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_admin())
