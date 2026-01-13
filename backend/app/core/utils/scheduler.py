# app/core/utils/scheduler.py
"""Scheduler pour les tâches planifiées (cron jobs)."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config.logger import logger


class AppScheduler:
    """Gestionnaire de tâches planifiées pour l'application."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = []

    def add_job(self, func, trigger, **trigger_args):
        """
        Ajoute une tâche planifiée.

        Args:
            func: Fonction à exécuter
            trigger: Type de trigger ('cron', 'interval', 'date')
            **trigger_args: Arguments du trigger (hour, minute, etc.)
        """
        job = self.scheduler.add_job(func, trigger, **trigger_args)
        self._jobs.append(job)
        logger.info(f"✅ Job scheduled: {func.__name__} with trigger {trigger} {trigger_args}")
        return job

    def start(self):
        """Démarre le scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Scheduler started")
        else:
            logger.warning("Scheduler already running")

    def shutdown(self, wait=True):
        """Arrête le scheduler proprement."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("🛑 Scheduler stopped")


# Instance globale du scheduler
app_scheduler = AppScheduler()
