"""
Jobs de nettoyage automatique pour les validations expirées.

Ce module contient les tâches CRON de nettoyage.
"""

from config.logger import logger
from app.database.db import get_connection


async def expire_validations():
    """
    Expire toutes les validations pending de plus de 2h.

    Cette fonction est appelée périodiquement (toutes les 15 minutes)
    pour nettoyer les validations en attente trop anciennes.
    """
    try:
        conn = await get_connection()
        try:
            # Récupérer les validations à expirer
            rows = await conn.fetch(
                """SELECT id FROM validations
                   WHERE status = 'pending'
                   AND created_at < NOW() - INTERVAL '2 hours'"""
            )

            if not rows:
                logger.debug("Aucune validation à expirer")
                return

            expired_count = 0
            for row in rows:
                validation_id = row['id']
                try:
                    # Marquer comme expired
                    await conn.execute(
                        """UPDATE validations
                           SET status = 'cancelled', expired_at = NOW()
                           WHERE id = $1""",
                        validation_id
                    )
                    expired_count += 1
                    logger.info(f"Validation expirée: {validation_id}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'expiration de {validation_id}: {e}")

            logger.info(f"Nettoyage terminé: {expired_count} validation(s) expirée(s)")

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Erreur dans le job d'expiration des validations: {e}")
