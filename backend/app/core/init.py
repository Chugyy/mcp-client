"""
Initialisation des ressources système au démarrage de l'application.
"""
import logging

logger = logging.getLogger("APP - Backend")


async def initialize_system_resources():
    """
    Point d'entrée pour initialisations supplémentaires si nécessaire.

    Note: La synchronisation principale de l'infrastructure système
    se fait via sync_internal_infrastructure() appelée dans main.py
    """
    logger.info("✅ System resources initialized")
    # Futurs hooks d'initialisation personnalisés ici si besoin
