"""
Utilitaires pour vérifier la santé des automations.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from config.logger import logger


async def check_automation_health(
    automation: Dict,
    executions: List[Dict],
    triggers: List[Dict],
    steps: List[Dict]
) -> Dict[str, Any]:
    """
    Vérifie la santé d'une automation.

    Args:
        automation: Automation à vérifier
        executions: Liste des exécutions récentes
        triggers: Liste des triggers configurés
        steps: Liste des workflow steps

    Returns:
        {
            'status': 'healthy' | 'warning' | 'error',
            'issues': List[str],
            'should_disable': bool
        }
    """
    issues = []
    status = 'healthy'
    should_disable = False

    # 1. Vérifier qu'il y a des triggers actifs
    active_triggers = [t for t in triggers if t.get('enabled', False)]
    if not active_triggers:
        issues.append("Aucun trigger actif")
        status = 'warning'

    # 2. Vérifier qu'il y a des workflow steps
    if not steps or len(steps) == 0:
        issues.append("Aucune étape configurée")
        status = 'error'
        should_disable = True

    # 3. Vérifier les steps désactivés
    if steps:
        disabled_steps = [s for s in steps if not s.get('enabled', True)]
        if len(disabled_steps) == len(steps):
            issues.append("Toutes les étapes sont désactivées")
            status = 'error'
            should_disable = True

    # 4. Vérifier le taux d'échec (sur les 10 dernières exécutions)
    if executions and len(executions) >= 10:
        recent_executions = executions[:10]
        failed_count = sum(1 for e in recent_executions if e.get('status') == 'failed')
        failure_rate = failed_count / len(recent_executions)

        if failure_rate >= 0.8:  # 80% ou plus d'échecs
            issues.append(f"Taux d'échec élevé: {failure_rate*100:.0f}%")
            status = 'error'
            should_disable = True
        elif failure_rate >= 0.5:  # 50% ou plus d'échecs
            issues.append(f"Taux d'échec modéré: {failure_rate*100:.0f}%")
            if status == 'healthy':
                status = 'warning'

    # 5. Vérifier l'ancienneté de la dernière exécution (si automation active)
    if automation.get('status') == 'active' and automation.get('enabled'):
        if executions and len(executions) > 0:
            last_exec = executions[0]
            last_date_str = last_exec.get('started_at')

            if last_date_str:
                try:
                    # Parser la date (format ISO 8601)
                    if isinstance(last_date_str, str):
                        last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                    else:
                        last_date = last_date_str

                    days_since = (datetime.now(last_date.tzinfo) - last_date).days

                    if days_since > 30:
                        issues.append(f"Aucune exécution depuis {days_since} jours")
                        if status == 'healthy':
                            status = 'warning'
                except Exception as e:
                    logger.warning(f"Failed to parse execution date: {e}")

    # 6. Valider les triggers CRON
    for trigger in triggers:
        if trigger.get('trigger_type') == 'cron' and trigger.get('enabled'):
            cron_expr = trigger.get('config', {}).get('cron_expression')
            if not cron_expr:
                issues.append("Trigger CRON sans expression")
                status = 'error'
                should_disable = True
            else:
                # Valider l'expression cron
                try:
                    from apscheduler.triggers.cron import CronTrigger
                    CronTrigger.from_crontab(cron_expr)
                except Exception as e:
                    issues.append(f"Expression CRON invalide: {cron_expr}")
                    status = 'error'
                    should_disable = True

    return {
        'status': status,
        'issues': issues,
        'should_disable': should_disable
    }


def calculate_automation_stats(executions: List[Dict]) -> Dict[str, Any]:
    """
    Calcule les statistiques d'une automation.

    Args:
        executions: Liste des exécutions

    Returns:
        {
            'total_executions': int,
            'success_count': int,
            'failed_count': int,
            'success_rate': float
        }
    """
    total = len(executions)
    success_count = sum(1 for e in executions if e.get('status') == 'success')
    failed_count = sum(1 for e in executions if e.get('status') == 'failed')
    success_rate = (success_count / total * 100) if total > 0 else 0

    return {
        'total_executions': total,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': round(success_rate, 2)
    }


def format_last_execution(execution: Optional[Dict]) -> Optional[Dict]:
    """
    Formate la dernière exécution pour l'API.

    Args:
        execution: Exécution à formater

    Returns:
        Exécution formatée ou None
    """
    if not execution:
        return None

    # Calculer la durée si completed_at existe
    duration_ms = None
    if execution.get('completed_at') and execution.get('started_at'):
        try:
            started = datetime.fromisoformat(execution['started_at'].replace('Z', '+00:00'))
            completed = datetime.fromisoformat(execution['completed_at'].replace('Z', '+00:00'))
            duration_ms = int((completed - started).total_seconds() * 1000)
        except:
            pass

    return {
        'id': execution.get('id'),
        'status': execution.get('status'),
        'started_at': execution.get('started_at'),
        'completed_at': execution.get('completed_at'),
        'duration_ms': duration_ms
    }
