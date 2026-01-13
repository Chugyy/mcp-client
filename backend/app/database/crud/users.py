import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# USERS
# ============================

async def create_user(email: str, password: str, name: str,
                     preferences: dict = None) -> str:
    """
    Crée un utilisateur et retourne son ID.

    Args:
        email: Email unique
        password: Mot de passe hashé
        name: Nom complet
        preferences: Préférences JSONB (défaut: {"theme":"system","language":"fr"})

    Returns:
        ID de l'utilisateur créé (format: usr_xxxxxx)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        user_id = generate_id('user')
        if preferences is None:
            preferences = {"theme": "system", "language": "fr"}

        await conn.execute(
            """INSERT INTO users (id, email, password, name, preferences)
               VALUES ($1, $2, $3, $4, $5::jsonb)""",
            user_id, email, password, name, json.dumps(preferences)
        )
        return user_id

async def get_user(user_id: str) -> Optional[Dict]:
    """Récupère un utilisateur par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(result) if result else None

async def get_user_by_email(email: str) -> Optional[Dict]:
    """Récupère un utilisateur par email."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        return dict(result) if result else None

async def list_users() -> List[Dict]:
    """Liste tous les utilisateurs."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in rows]

async def update_user(user_id: str, name: str = None,
                     preferences: dict = None) -> bool:
    """Met à jour un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if preferences is not None:
            updates.append(f"preferences = ${param_count}::jsonb")
            params.append(json.dumps(preferences))
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def update_user_password(user_id: str, password: str) -> bool:
    """Met à jour le mot de passe d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET password = $1, updated_at = NOW() WHERE id = $2",
            password, user_id
        )
        return int(result.split()[1]) > 0

async def delete_user(user_id: str) -> bool:
    """Supprime un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        return int(result.split()[1]) > 0

# ============================
# RESET TOKENS
# ============================

async def create_reset_token(user_id: str, token: str, expires_at: datetime) -> str:
    """Crée un token de réinitialisation."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        token_id = generate_id('reset_token')
        await conn.execute(
            """INSERT INTO reset_tokens (id, user_id, token, expires_at)
               VALUES ($1, $2, $3, $4)""",
            token_id, user_id, token, expires_at
        )
        return token_id

async def get_reset_token(token: str) -> Optional[Dict]:
    """Récupère un token de réinitialisation valide (non utilisé)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM reset_tokens WHERE token = $1 AND used = FALSE",
            token
        )
        return dict(result) if result else None

async def mark_token_used(token: str) -> bool:
    """Marque un token comme utilisé."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE reset_tokens SET used = TRUE WHERE token = $1",
            token
        )
        return int(result.split()[1]) > 0
