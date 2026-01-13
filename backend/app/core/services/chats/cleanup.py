# app/core/services/chats/cleanup.py
"""Service de nettoyage des chats vides."""

from typing import Dict, Any
from config.logger import logger
from app.database import crud


async def daily_empty_chats_cleanup_job(days: int = 30) -> Dict[str, Any]:
    """
    Job quotidien de nettoyage des chats vides.
    Supprime les chats sans messages datant de plus de X jours.

    Args:
        days: Nombre de jours avant suppression (défaut: 30)

    Returns:
        Dict contenant le nombre de chats supprimés et les statistiques
    """
    logger.info(f"🧹 Starting daily empty chats cleanup job (older than {days} days)...")

    try:
        # Récupérer les statistiques avant nettoyage
        stats_before = await crud.get_empty_chats_stats()
        logger.info(f"📊 Stats before cleanup: {stats_before}")

        # Supprimer les chats vides
        deleted_count = await crud.delete_empty_chats_older_than(days=days)

        # Récupérer les statistiques après nettoyage
        stats_after = await crud.get_empty_chats_stats()

        logger.info(f"✅ Cleanup completed: {deleted_count} chats deleted")
        logger.info(f"📊 Stats after cleanup: {stats_after}")

        return {
            "deleted_count": deleted_count,
            "stats_before": stats_before,
            "stats_after": stats_after
        }

    except Exception as e:
        logger.error(f"❌ Daily cleanup job failed: {e}")
        raise
