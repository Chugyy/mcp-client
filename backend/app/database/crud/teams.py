import asyncpg
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# TEAMS
# ============================

async def create_team(name: str, system_prompt: str, description: str = None,
                     tags: List[str] = None, enabled: bool = True) -> str:
    """Crée une équipe."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        team_id = generate_id('team')
        await conn.execute(
            """INSERT INTO teams (id, name, description, system_prompt, tags, enabled)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            team_id, name, description, system_prompt, tags or [], enabled
        )
        return team_id

async def get_team(team_id: str) -> Optional[Dict]:
    """Récupère une équipe par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM teams WHERE id = $1", team_id)
        return dict(result) if result else None

async def list_teams(enabled_only: bool = False) -> List[Dict]:
    """Liste toutes les équipes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                "SELECT * FROM teams WHERE enabled = TRUE ORDER BY created_at DESC"
            )
        else:
            rows = await conn.fetch("SELECT * FROM teams ORDER BY created_at DESC")
        return [dict(row) for row in rows]

async def update_team(team_id: str, name: str = None, description: str = None,
                     system_prompt: str = None, tags: List[str] = None,
                     enabled: bool = None) -> bool:
    """Met à jour une équipe."""
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
        params.append(team_id)

        query = f"UPDATE teams SET {', '.join(updates)} WHERE id = ${param_count}"
        result = await conn.execute(query, *params)
        return int(result.split()[1]) > 0

async def delete_team(team_id: str) -> bool:
    """Supprime une équipe."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM teams WHERE id = $1", team_id)
        return int(result.split()[1]) > 0

# ============================
# MEMBERSHIPS
# ============================

async def add_member(team_id: str, agent_id: str, enabled: bool = True) -> str:
    """Ajoute un agent à une équipe."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        membership_id = generate_id('membership')
        await conn.execute(
            """INSERT INTO memberships (id, team_id, agent_id, enabled)
               VALUES ($1, $2, $3, $4)""",
            membership_id, team_id, agent_id, enabled
        )
        return membership_id

async def get_membership(membership_id: str) -> Optional[Dict]:
    """Récupère un membership par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM memberships WHERE id = $1", membership_id)
        return dict(result) if result else None

async def remove_member(team_id: str, agent_id: str) -> bool:
    """Retire un agent d'une équipe."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM memberships WHERE team_id = $1 AND agent_id = $2",
            team_id, agent_id
        )
        return int(result.split()[1]) > 0

async def list_team_members(team_id: str, enabled_only: bool = False) -> List[Dict]:
    """Liste les membres (agents) d'une équipe."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled_only:
            rows = await conn.fetch(
                """SELECT a.* FROM agents a
                   INNER JOIN memberships m ON m.agent_id = a.id
                   WHERE m.team_id = $1 AND m.enabled = TRUE
                   ORDER BY m.created_at DESC""",
                team_id
            )
        else:
            rows = await conn.fetch(
                """SELECT a.* FROM agents a
                   INNER JOIN memberships m ON m.agent_id = a.id
                   WHERE m.team_id = $1
                   ORDER BY m.created_at DESC""",
                team_id
            )
        return [dict(row) for row in rows]

async def get_agent_teams(agent_id: str) -> List[Dict]:
    """Liste les équipes dont un agent fait partie."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT t.* FROM teams t
               INNER JOIN memberships m ON m.team_id = t.id
               WHERE m.agent_id = $1 AND m.enabled = TRUE
               ORDER BY m.created_at DESC""",
            agent_id
        )
        return [dict(row) for row in rows]
