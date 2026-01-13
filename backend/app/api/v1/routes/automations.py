from fastapi import APIRouter, Depends, status, Request, Header
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException, ConflictError
from typing import List, Optional
from datetime import datetime
from app.database import crud
from app.core.services.automation.executor import execute_automation
from app.core.services.automation.scheduler import register_trigger, unregister_trigger
from app.core.services.automation.manager import AutomationManager
from app.core.validators.automation import AutomationValidator
from app.api.v1.schemas.automation import (
    AutomationCreate,
    AutomationUpdate,
    WorkflowStepCreate,
    WorkflowStepUpdate,
    TriggerCreate,
    TriggerUpdate,
    ExecutionParams,
    TriggerType
)
from app.core.utils.auth import get_current_user
from app.core.utils.permissions import can_access_automation
from app.database.models import User
from config.logger import logger

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("")
async def list_automations(
    include_enriched: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Liste les automations de l'utilisateur avec stats enrichies."""
    automations = await crud.list_automations(user_id=current_user.id)

    if include_enriched:
        automations = await AutomationManager.enrich_automations(automations)

    return automations


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_automation(
    request: AutomationCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle automation."""
    automation_id = await AutomationManager.create(
        dto=request,
        user_id=current_user.id,
        is_admin=current_user.is_system
    )

    automation = await crud.get_automation(automation_id)
    return automation


@router.get("/{automation_id}")
async def get_automation(
    automation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère une automation par ID."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to access this automation")

    return automation


@router.patch("/{automation_id}")
async def update_automation(
    automation_id: str,
    request: AutomationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour une automation."""
    updated_automation = await AutomationManager.update(
        automation_id=automation_id,
        dto=request,
        user_id=current_user.id
    )
    return updated_automation


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    automation_id: str,
    x_confirm: bool = Header(False, alias="X-Confirm-Deletion"),
    current_user: User = Depends(get_current_user)
):
    """Supprime une automation."""
    try:
        await AutomationManager.delete(
            automation_id=automation_id,
            user_id=current_user.id,
            force=x_confirm
        )
    except RuntimeError as e:
        # Impact détecté, retourner 409 avec détails
        automation = await crud.get_automation(automation_id)
        triggers = await crud.get_triggers(automation_id)
        from app.database.crud.executions import list_executions
        executions = await list_executions(automation_id)

        impact = {
            "type": "confirmation_required",
            "impact": {
                "automation_name": automation.get("name"),
                "triggers_count": len(triggers),
                "executions_count": len(executions),
                "last_execution_date": executions[0].get("started_at") if executions else None
            }
        }
        raise ConflictError(impact)

    return None


@router.post("/{automation_id}/execute")
async def execute_automation_endpoint(
    automation_id: str,
    body: ExecutionParams = ExecutionParams(),
    current_user: User = Depends(get_current_user)
):
    """Exécute une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to execute this automation")

    try:
        result = await execute_automation(
            automation_id=automation_id,
            params=body.params
        )
        return result
    except Exception as e:
        logger.error(f"Failed to execute automation: {e}")
        raise AppException(str(e))


@router.get("/{automation_id}/executions")
async def list_automation_executions(
    automation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Liste toutes les executions d'une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to access this automation")

    try:
        executions = await crud.list_executions(automation_id)
        return executions
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise AppException(str(e))


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère les logs d'exécution enrichis avec les infos des steps."""
    execution = await crud.get_execution(execution_id)

    if not execution:
        raise NotFoundError("Execution not found")

    # Vérifier ownership de l'automation associée
    automation_id = execution.get("automation_id")
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Associated automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to access these logs")

    try:
        # 1. Récupérer les logs
        logs = await crud.get_execution_step_logs(execution_id)

        # 2. Récupérer les workflow steps pour enrichir
        steps = await crud.get_workflow_steps(automation_id)
        steps_by_id = {step["id"]: step for step in steps}

        # 3. Enrichir les logs avec les infos des steps
        enriched_logs = []
        for log in logs:
            step_id = log.get("step_id")
            step = steps_by_id.get(step_id, {})

            enriched_logs.append({
                **log,
                "step_order": step.get("step_order"),
                "step_name": step.get("step_name"),
                "step_type": step.get("step_type"),
                "step_subtype": step.get("step_subtype")
            })

        return enriched_logs
    except Exception as e:
        logger.error(f"Failed to get execution logs: {e}")
        raise AppException(str(e))


@router.post("/{automation_id}/steps", status_code=status.HTTP_201_CREATED)
async def create_workflow_step(
    automation_id: str,
    request: WorkflowStepCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée un workflow step pour une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to modify this automation")

    # Valider config selon step_type/subtype
    await AutomationValidator.validate_step_config(
        step_type=request.step_type,
        step_subtype=request.step_subtype,
        config=request.config
    )

    step_id = await crud.create_workflow_step(
        automation_id=automation_id,
        step_order=request.step_order,
        step_name=request.step_name,
        step_type=request.step_type,
        step_subtype=request.step_subtype,
        config=request.config,
        run_condition=request.run_condition,
        enabled=request.enabled
    )

    step = await crud.get_workflow_step(step_id)
    return step


@router.get("/{automation_id}/steps")
async def list_workflow_steps(
    automation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Liste les workflow steps d'une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to access this automation")

    try:
        steps = await crud.get_workflow_steps(automation_id)
        return steps
    except Exception as e:
        logger.error(f"Failed to list workflow steps: {e}")
        raise AppException(str(e))


@router.patch("/steps/{step_id}")
async def update_workflow_step(
    step_id: str,
    request: WorkflowStepUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour un workflow step."""
    from app.database.crud import workflow_steps as step_crud

    # Récupérer le step
    step = await step_crud.get_workflow_step(step_id)
    if not step:
        raise NotFoundError("Workflow step not found")

    # Vérifier ownership de l'automation
    automation = await crud.get_automation(step.get("automation_id"))
    if not automation:
        raise NotFoundError("Associated automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to modify this workflow step")

    # Valider config si fournie
    if request.config is not None and request.step_subtype:
        await AutomationValidator.validate_step_config(
            step_type=request.step_type or step.get("step_type"),
            step_subtype=request.step_subtype,
            config=request.config
        )

    # Construire les updates
    updates = {}
    if request.step_order is not None:
        updates["step_order"] = request.step_order
    if request.step_name is not None:
        updates["step_name"] = request.step_name
    if request.step_type is not None:
        updates["step_type"] = request.step_type
    if request.step_subtype is not None:
        updates["step_subtype"] = request.step_subtype
    if request.config is not None:
        updates["config"] = request.config
    if request.run_condition is not None:
        updates["run_condition"] = request.run_condition
    if request.enabled is not None:
        updates["enabled"] = request.enabled

    if not updates:
        raise ValidationError("No fields to update")

    success = await step_crud.update_workflow_step(step_id, **updates)
    if not success:
        raise AppException("Failed to update workflow step")

    return await step_crud.get_workflow_step(step_id)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow_step(
    step_id: str,
    current_user: User = Depends(get_current_user)
):
    """Supprime un workflow step."""
    from app.database.crud import workflow_steps as step_crud

    # Récupérer le step
    step = await step_crud.get_workflow_step(step_id)
    if not step:
        raise NotFoundError("Workflow step not found")

    # Vérifier ownership de l'automation
    automation = await crud.get_automation(step.get("automation_id"))
    if not automation:
        raise NotFoundError("Associated automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to delete this workflow step")

    success = await step_crud.delete_workflow_step(step_id)
    if not success:
        raise AppException("Failed to delete workflow step")

    return None


@router.post("/{automation_id}/triggers", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    automation_id: str,
    request: TriggerCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée un trigger pour une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to modify this automation")

    # Valider config selon trigger_type
    await AutomationValidator.validate_trigger_config(
        trigger_type=request.trigger_type,
        config=request.config
    )

    trigger_id = await crud.create_trigger(
        automation_id=automation_id,
        trigger_type=request.trigger_type,
        config=request.config,
        enabled=request.enabled
    )

    trigger = await crud.get_trigger(trigger_id)

    # Si CRON actif, l'enregistrer
    if request.trigger_type == TriggerType.CRON and request.enabled:
        cron_expr = request.config.get("cron_expression")
        if cron_expr:
            try:
                await register_trigger(automation_id, trigger_id, cron_expr)
            except Exception as e:
                logger.error(f"Failed to register CRON trigger: {e}")

    return trigger


@router.get("/{automation_id}/triggers")
async def list_triggers(
    automation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Liste les triggers d'une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to access this automation")

    try:
        triggers = await crud.get_triggers(automation_id)
        return triggers
    except Exception as e:
        logger.error(f"Failed to list triggers: {e}")
        raise AppException(str(e))


@router.patch("/triggers/{trigger_id}")
async def update_trigger(
    trigger_id: str,
    request: TriggerUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour un trigger."""
    from app.database.crud import triggers as trigger_crud

    # Récupérer le trigger
    trigger = await trigger_crud.get_trigger(trigger_id)
    if not trigger:
        raise NotFoundError("Trigger not found")

    # Vérifier ownership de l'automation
    automation = await crud.get_automation(trigger.get("automation_id"))
    if not automation:
        raise NotFoundError("Associated automation not found")

    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to modify this trigger")

    # Valider config si fournie
    if request.config is not None and request.trigger_type:
        await AutomationValidator.validate_trigger_config(
            trigger_type=request.trigger_type,
            config=request.config
        )

    # Construire les updates
    updates = {}
    if request.trigger_type is not None:
        updates["trigger_type"] = request.trigger_type
    if request.config is not None:
        updates["config"] = request.config
    if request.enabled is not None:
        # Si on désactive un trigger CRON, le désenregistrer
        if not request.enabled and trigger.get("trigger_type") == "cron":
            try:
                await unregister_trigger(trigger.get("automation_id"), trigger_id)
            except Exception as e:
                logger.error(f"Failed to unregister CRON trigger: {e}")
        # Si on active un trigger CRON, l'enregistrer
        elif request.enabled and trigger.get("trigger_type") == "cron":
            cron_expr = (request.config or trigger.get("config", {})).get("cron_expression")
            if cron_expr:
                try:
                    await register_trigger(trigger.get("automation_id"), trigger_id, cron_expr)
                except Exception as e:
                    logger.error(f"Failed to register CRON trigger: {e}")
        updates["enabled"] = request.enabled

    if not updates:
        raise ValidationError("No fields to update")

    success = await trigger_crud.update_trigger(trigger_id, **updates)
    if not success:
        raise AppException("Failed to update trigger")

    return await trigger_crud.get_trigger(trigger_id)


@router.delete("/{automation_id}/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(
    automation_id: str,
    trigger_id: str,
    current_user: User = Depends(get_current_user)
):
    """Supprime un trigger d'une automation."""
    automation = await crud.get_automation(automation_id)

    if not automation:
        raise NotFoundError("Automation not found")

    # Vérifier ownership
    if not can_access_automation(current_user, automation):
        raise PermissionError("Not authorized to modify this automation")

    # Récupérer le trigger
    trigger = await crud.get_trigger(trigger_id)
    if not trigger:
        raise NotFoundError("Trigger not found")

    # Vérifier que le trigger appartient bien à cette automation
    if trigger.get("automation_id") != automation_id:
        raise PermissionError("Trigger does not belong to this automation")

    try:
        # Si c'est un trigger CRON, le désenregistrer du scheduler
        if trigger.get("trigger_type") == "cron":
            try:
                await unregister_trigger(automation_id, trigger_id)
            except Exception as e:
                logger.error(f"Failed to unregister CRON trigger: {e}")

        # Supprimer le trigger de la BDD
        success = await crud.delete_trigger(trigger_id)
        if not success:
            raise AppException("Failed to delete trigger")

        return None
    except Exception as e:
        logger.error(f"Failed to delete trigger: {e}")
        raise AppException(str(e))


@router.post("/webhook/{automation_id}/{token}", include_in_schema=True, tags=["webhooks"])
async def trigger_webhook(
    automation_id: str,
    token: str,
    request: Request
):
    """
    Endpoint PUBLIC pour déclencher une automation via webhook.

    - NON AUTHENTIFIÉ : Utilise le token dans l'URL pour la sécurité
    - Le token est vérifié contre le hash stocké dans le trigger
    - Les paramètres sont extraits du body JSON et/ou query params

    Example:
        POST /webhook/auto_abc123/my-secret-token-xyz
        Body: {"user_id": "123", "event": "purchase"}
    """
    from app.core.utils.security import verify_webhook_secret
    import json

    # 1. Vérifier que l'automation existe
    automation = await crud.get_automation(automation_id)
    if not automation:
        raise NotFoundError("Automation not found")

    # 2. Vérifier que l'automation est activée
    if not automation.get("enabled", False):
        raise PermissionError("Automation is disabled")

    # 3. Récupérer les triggers de cette automation
    from app.database.db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer les triggers avec le hash réel (pas masqué)
        rows = await conn.fetch(
            """SELECT id, trigger_type, config, enabled
               FROM automation.triggers
               WHERE automation_id = $1""",
            automation_id
        )

        # 4. Trouver le trigger webhook actif
        webhook_trigger = None
        for row in rows:
            trigger_dict = dict(row)
            if isinstance(trigger_dict.get('config'), str):
                trigger_dict['config'] = json.loads(trigger_dict['config'])

            if (trigger_dict.get("trigger_type") == "webhook" and
                trigger_dict.get("enabled", True)):
                webhook_trigger = trigger_dict
                break

        if not webhook_trigger:
            raise NotFoundError("No active webhook trigger found for this automation"
            )

        # 5. Vérifier le token (contre le hash stocké en BDD)
        stored_hash = webhook_trigger["config"].get("secret")

        if not stored_hash:
            raise AppException("Webhook trigger is not properly configured (missing secret)"
            )

        # Vérifier que le token fourni correspond au hash
        if not verify_webhook_secret(token, stored_hash):
            raise PermissionError("Invalid webhook token")

    # 6. Extraire les paramètres (query params + body JSON)
    query_params = dict(request.query_params)

    try:
        body = await request.json()
    except:
        # Si pas de body JSON, utiliser seulement les query params
        body = {}

    # 7. Enrichir avec métadonnées
    params = {
        **body,
        **query_params,
        "_webhook": {
            "received_at": datetime.now().isoformat(),
            "automation_id": automation_id,
            "trigger_id": webhook_trigger["id"],
            "source_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    }

    # 8. Exécuter l'automation
    try:
        result = await execute_automation(
            automation_id=automation_id,
            trigger_id=webhook_trigger["id"],
            params=params
        )

        return {
            "execution_id": result.get("execution_id"),
            "status": result.get("status")
        }

    except Exception as e:
        logger.error(f"Webhook execution failed: {e}")
        raise AppException(f"Automation execution failed: {str(e)}")
