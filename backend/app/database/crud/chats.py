import asyncpg
import json
from typing import Optional, Dict, List
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# CHATS
# ============================

async def create_chat(user_id: str, title: str, agent_id: str = None,
                     team_id: str = None) -> str:
    """Crée un chat."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        chat_id = generate_id('chat')
        await conn.execute(
            """INSERT INTO chats (id, user_id, agent_id, team_id, title)
               VALUES ($1, $2, $3, $4, $5)""",
            chat_id, user_id, agent_id, team_id, title
        )
        return chat_id

async def get_chat(chat_id: str) -> Optional[Dict]:
    """Récupère un chat par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM chats WHERE id = $1", chat_id)
        return dict(result) if result else None

async def list_chats_by_user(user_id: str) -> List[Dict]:
    """Liste tous les chats d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM chats WHERE user_id = $1 ORDER BY updated_at DESC",
            user_id
        )
        return [dict(row) for row in rows]

async def update_chat_title(chat_id: str, title: str) -> bool:
    """Met à jour le titre d'un chat."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE chats SET title = $1, updated_at = NOW() WHERE id = $2",
            title, chat_id
        )
        return int(result.split()[1]) > 0

async def delete_chat(chat_id: str) -> bool:
    """Supprime un chat."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM chats WHERE id = $1", chat_id)
        return int(result.split()[1]) > 0

async def set_validation_pending(chat_id: str, validation_id: Optional[str]) -> bool:
    """Définit ou clear la validation en attente pour un chat."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE chats SET awaiting_validation_id = $1, updated_at = NOW() WHERE id = $2",
            validation_id, chat_id
        )
        return int(result.split()[1]) > 0

# ============================
# MESSAGES
# ============================

async def create_message(chat_id: str, role: str, content: str,
                    metadata: dict = None, turn_id: str = None,
                    sequence_index: int = None) -> str:
    """Crée un message dans un chat avec support de turn_id et sequence_index."""
    import json as json_module
    from config.logger import logger

    pool = await get_pool()
    async with pool.acquire() as conn:
        message_id = generate_id('message')
        # Convertir metadata en JSON string pour PostgreSQL JSONB
        metadata_json = json_module.dumps(metadata or {})
        await conn.execute(
            """INSERT INTO messages (id, chat_id, role, content, metadata, turn_id, sequence_index)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)""",
            message_id, chat_id, role, content, metadata_json, turn_id, sequence_index
        )

        # LOG: Création de message
        content_preview = content[:50] + "..." if len(content) > 50 else content
        logger.info(f"📝 CREATE_MESSAGE | id={message_id} | role={role} | turn_id={turn_id} | seq={sequence_index} | content='{content_preview}'")

        return message_id

async def get_messages_by_chat(chat_id: str, limit: int = 100) -> List[Dict]:
    """Récupère les messages d'un chat."""
    from config.logger import logger

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM messages
               WHERE chat_id = $1
               ORDER BY created_at ASC
               LIMIT $2""",
            chat_id, limit
        )

        # LOG: Ordre des messages récupérés
        logger.info(f"📥 GET_MESSAGES | chat_id={chat_id} | count={len(rows)}")
        for i, row in enumerate(rows):
            content_preview = row['content'][:30] + "..." if len(row['content']) > 30 else row['content']
            logger.info(f"   [{i}] role={row['role']} | created_at={row['created_at']} | content='{content_preview}'")

        return [dict(row) for row in rows]

async def delete_message(message_id: str) -> bool:
    """Supprime un message."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM messages WHERE id = $1", message_id)
        return int(result.split()[1]) > 0

async def get_message(message_id: str):
    """Récupère un message par ID et retourne un objet Message."""
    from app.database.models import Message
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM messages WHERE id = $1", message_id)
        if not result:
            return None
        return Message.from_row(result)

async def update_message_content_and_metadata(
    message_id: str,
    content: str,
    metadata: dict
) -> bool:
    """Met à jour le contenu et les metadata d'un message."""
    import json as json_module
    pool = await get_pool()
    async with pool.acquire() as conn:
        metadata_json = json_module.dumps(metadata)
        result = await conn.execute(
            """UPDATE messages
               SET content = $1, metadata = $2::jsonb
               WHERE id = $3""",
            content, metadata_json, message_id
        )
        return int(result.split()[1]) > 0

async def update_message_turn_info(message_id: str, turn_id: str, sequence_index: int) -> bool:
    """Met à jour le turn_id et sequence_index d'un message."""
    from config.logger import logger

    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE messages
               SET turn_id = $1, sequence_index = $2
               WHERE id = $3""",
            turn_id, sequence_index, message_id
        )

        # LOG: Mise à jour turn_info
        logger.info(f"🔄 UPDATE_TURN_INFO | id={message_id} | turn_id={turn_id} | seq={sequence_index}")

        return int(result.split()[1]) > 0


# ============================
# CHAT INITIALIZATION
# ============================

async def initialize_chat(chat_id: str, agent_id: str, model: str) -> bool:
    """Initialize a chat with agent and model. Raises ValueError if already initialized."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if chat exists and is not already initialized
        chat = await conn.fetchrow(
            "SELECT initialized_at FROM chats WHERE id = $1",
            chat_id
        )

        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        if chat['initialized_at'] is not None:
            raise ValueError(f"Chat {chat_id} is already initialized")

        # Update chat with agent, model and initialized_at
        result = await conn.execute(
            """UPDATE chats
               SET agent_id = $1, model = $2, initialized_at = NOW(), updated_at = NOW()
               WHERE id = $3 AND initialized_at IS NULL""",
            agent_id, model, chat_id
        )

        return int(result.split()[1]) > 0

async def delete_empty_chats_older_than(days: int = 30) -> int:
    """Delete chats that are not initialized and older than specified days."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """DELETE FROM chats
               WHERE initialized_at IS NULL
               AND created_at < NOW() - INTERVAL '%s days'""",
            days
        )
        return int(result.split()[1])

async def get_empty_chats_stats() -> Dict[str, int]:
    """Get statistics about empty (non-initialized) chats."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Total empty chats
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM chats WHERE initialized_at IS NULL"
        )

        # Less than 24 hours
        less_than_24h = await conn.fetchval(
            """SELECT COUNT(*) FROM chats
               WHERE initialized_at IS NULL
               AND created_at > NOW() - INTERVAL '24 hours'"""
        )

        # Less than 7 days
        less_than_7days = await conn.fetchval(
            """SELECT COUNT(*) FROM chats
               WHERE initialized_at IS NULL
               AND created_at > NOW() - INTERVAL '7 days'"""
        )

        # Older than 30 days
        older_than_30days = await conn.fetchval(
            """SELECT COUNT(*) FROM chats
               WHERE initialized_at IS NULL
               AND created_at < NOW() - INTERVAL '30 days'"""
        )

        return {
            "total": total or 0,
            "less_than_24h": less_than_24h or 0,
            "less_than_7days": less_than_7days or 0,
            "older_than_30days": older_than_30days or 0
        }

# ============================
# IMPACT ANALYSIS
# ============================

async def count_chats_by_agent(agent_id: str) -> int:
    """Compte le nombre de chats rattachés à un agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM chats WHERE agent_id = $1",
            agent_id
        )
        return count or 0

async def count_chats_by_team(team_id: str) -> int:
    """Compte le nombre de chats rattachés à une team."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM chats WHERE team_id = $1",
            team_id
        )
        return count or 0

async def update_chat_model(chat_id: str, model: str) -> bool:
    """Met à jour le modèle d'un chat (cache du dernier modèle utilisé)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE chats
               SET model = $1, updated_at = NOW()
               WHERE id = $2""",
            model, chat_id
        )
        return int(result.split()[1]) > 0

# ============================
# GENERATION LOCKING
# ============================

async def update_chat_generating_status(chat_id: str, is_generating: bool) -> bool:
    """
    Met à jour le statut de génération d'un chat.

    Args:
        chat_id: ID du chat
        is_generating: True si génération en cours, False sinon

    Returns:
        True si mise à jour réussie

    Usage:
        - Appeler avec True au début d'un stream
        - Appeler avec False à la fin du stream (dans finally)
        - Utilisé pour bloquer messages concurrents (erreur 409)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE chats
               SET is_generating = $1, updated_at = NOW()
               WHERE id = $2""",
            is_generating, chat_id
        )
        return int(result.split()[1]) > 0

async def is_chat_generating(chat_id: str) -> bool:
    """
    Vérifie si le chat est en cours de génération.

    Args:
        chat_id: ID du chat

    Returns:
        True si génération en cours, False sinon

    Usage:
        - Vérifier avant d'accepter un nouveau message
        - Retourner 409 si True
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT is_generating FROM chats WHERE id = $1",
            chat_id
        )
        return result if result is not None else False


async def get_message_by_validation_id(validation_id: str):
    """Récupère le message tool_call associé à une validation."""
    from app.database.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM messages
               WHERE metadata->>'validation_id' = $1
               AND role = 'tool_call'
               ORDER BY created_at DESC
               LIMIT 1""",
            validation_id
        )
        if not row:
            return None

        # Convertir en dict
        from app.database.models import Message
        return Message.from_row(row)


async def update_message_metadata(message_id: str, metadata_updates: dict):
    """Met à jour partiellement les métadonnées d'un message."""
    import json
    from app.database.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE messages
               SET metadata = metadata || $1::jsonb,
                   updated_at = NOW()
               WHERE id = $2""",
            json.dumps(metadata_updates),
            message_id
        )
