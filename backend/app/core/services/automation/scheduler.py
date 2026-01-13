"""
Service de gestion des triggers CRON pour les automations.

Ce module permet de :
- Charger tous les triggers CRON au démarrage
- Enregistrer/désenregistrer des triggers dynamiquement
- Gérer le cycle de vie des jobs APScheduler
"""

from apscheduler.triggers.cron import CronTrigger
from config.logger import logger
from app.core.utils.scheduler import app_scheduler
from app.database import crud
from app.core.services.automation.executor import execute_automation


async def load_cron_triggers():
    """
    Charge tous les triggers CRON actifs au démarrage.

    Parcourt toutes les automations actives avec triggers CRON
    et les enregistre dans APScheduler.
    """
    try:
        # Récupérer toutes les automations avec triggers CRON actifs
        automations = await crud.list_cron_automations()

        if not automations:
            logger.info("Aucun trigger CRON actif à charger")
            return

        logger.info(f"Chargement de {len(automations)} automation(s) avec triggers CRON")

        # Pour chaque automation, récupérer ses triggers CRON
        for automation in automations:
            automation_id = automation['id']
            triggers = await crud.get_triggers(automation_id)

            for trigger in triggers:
                # Filtrer uniquement les triggers CRON actifs
                if trigger['trigger_type'] != 'cron' or not trigger.get('enabled', False):
                    continue

                trigger_id = trigger['id']
                config = trigger.get('config', {})
                cron_expression = config.get('cron_expression')

                if not cron_expression:
                    logger.warning(f"Trigger CRON {trigger_id} sans cron_expression, ignoré")
                    continue

                try:
                    # Enregistrer le trigger
                    await register_trigger(automation_id, trigger_id, cron_expression)
                except Exception as e:
                    logger.error(f"Erreur lors de l'enregistrement du trigger {trigger_id}: {e}")

        logger.info("Chargement des triggers CRON terminé")

    except Exception as e:
        logger.error(f"Erreur lors du chargement des triggers CRON: {e}")


async def register_trigger(automation_id: str, trigger_id: str, cron_expr: str):
    """
    Enregistre un trigger CRON dans APScheduler.

    Args:
        automation_id: ID de l'automation
        trigger_id: ID du trigger
        cron_expr: Expression CRON (ex: "0 9 * * 1-5")
    """
    try:
        # Parser l'expression CRON
        cron_trigger = CronTrigger.from_crontab(cron_expr)

        # Construire l'ID unique du job
        job_id = f"automation_{automation_id}_trigger_{trigger_id}"

        # Ajouter le job au scheduler
        app_scheduler.add_job(
            func=execute_automation,
            trigger=cron_trigger,
            args=[automation_id],
            kwargs={'trigger_id': trigger_id},
            id=job_id,
            replace_existing=True
        )

        logger.info(f"✅ CRON trigger registered: {job_id} ({cron_expr})")

    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du trigger {trigger_id}: {e}")
        raise


async def unregister_trigger(automation_id: str, trigger_id: str):
    """
    Désenregistre un trigger CRON d'APScheduler.

    Args:
        automation_id: ID de l'automation
        trigger_id: ID du trigger
    """
    try:
        # Construire l'ID du job
        job_id = f"automation_{automation_id}_trigger_{trigger_id}"

        # Supprimer le job du scheduler
        try:
            app_scheduler.scheduler.remove_job(job_id)
            logger.info(f"❌ CRON trigger unregistered: {job_id}")
        except Exception:
            # Le job n'existe peut-être pas, ce n'est pas une erreur
            logger.warning(f"Job {job_id} introuvable lors de la désinscription")

    except Exception as e:
        logger.error(f"Erreur lors de la désinscription du trigger {trigger_id}: {e}")
        raise
