"""Handlers pour les tools automation."""

from typing import Dict, Any
from app.core.system.handler import tool_handler
from config.logger import logger


@tool_handler("create_automation")
async def handle_create_automation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Crée une nouvelle automation."""
    from app.database.crud import automations as crud

    user_id = arguments.get("_user_id")
    name = arguments.get("name")
    description = arguments.get("description")
    enabled = arguments.get("enabled", True)

    if not name or not description:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameters: name, description"
        }

    automation_id = await crud.create_automation(
        user_id=user_id,
        name=name,
        description=description,
        enabled=enabled
    )

    return {
        "success": True,
        "result": {"automation_id": automation_id},
        "error": None
    }


@tool_handler("list_automations")
async def handle_list_automations(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste toutes les automations de l'utilisateur."""
    from app.database.crud import automations as crud

    user_id = arguments.get("_user_id")

    if not user_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: _user_id"
        }

    automations = await crud.list_automations(user_id=user_id)

    return {
        "success": True,
        "result": {
            "automations": automations,
            "total": len(automations)
        },
        "error": None
    }


@tool_handler("get_automation")
async def handle_get_automation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Récupère les détails d'une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    automation = await crud.get_automation(automation_id)

    if not automation:
        return {
            "success": False,
            "result": None,
            "error": f"Automation {automation_id} not found"
        }

    return {
        "success": True,
        "result": automation,
        "error": None
    }


@tool_handler("update_automation")
async def handle_update_automation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour une automation (nom, description, enabled)."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")
    name = arguments.get("name")
    description = arguments.get("description")
    enabled = arguments.get("enabled")

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    # Vérifier que l'automation existe
    automation = await crud.get_automation(automation_id)
    if not automation:
        return {
            "success": False,
            "result": None,
            "error": f"Automation {automation_id} not found"
        }

    # Construire les updates
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if enabled is not None:
        updates["enabled"] = enabled

    if not updates:
        return {
            "success": False,
            "result": None,
            "error": "No fields to update"
        }

    success = await crud.update_automation(automation_id, **updates)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to update automation"
        }

    # Retourner l'automation mise à jour
    updated_automation = await crud.get_automation(automation_id)

    return {
        "success": True,
        "result": updated_automation,
        "error": None
    }


@tool_handler("delete_automation")
async def handle_delete_automation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Supprime une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    # Vérifier que l'automation existe et n'est pas système
    automation = await crud.get_automation(automation_id)
    if not automation:
        return {
            "success": False,
            "result": None,
            "error": f"Automation {automation_id} not found"
        }

    if automation.get("is_system", False):
        return {
            "success": False,
            "result": None,
            "error": "Cannot delete system automation"
        }

    success = await crud.delete_automation(automation_id)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to delete automation"
        }

    return {
        "success": True,
        "result": {"automation_id": automation_id, "deleted": True},
        "error": None
    }


@tool_handler("add_workflow_step")
async def handle_add_workflow_step(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Ajoute une étape au workflow d'une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")
    step_order = arguments.get("step_order")
    step_name = arguments.get("step_name")
    step_type = arguments.get("step_type")
    step_subtype = arguments.get("step_subtype")
    config = arguments.get("config")
    run_condition = arguments.get("run_condition")

    if not all([automation_id, step_order is not None, step_name, step_type, step_subtype, config]):
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameters"
        }

    step_id = await crud.create_workflow_step(
        automation_id=automation_id,
        step_order=step_order,
        step_name=step_name,
        step_type=step_type,
        step_subtype=step_subtype,
        config=config,
        run_condition=run_condition
    )

    return {
        "success": True,
        "result": {"step_id": step_id},
        "error": None
    }


@tool_handler("list_workflow_steps")
async def handle_list_workflow_steps(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste toutes les étapes d'une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    steps = await crud.get_workflow_steps(automation_id)

    return {
        "success": True,
        "result": {
            "automation_id": automation_id,
            "steps": steps,
            "total": len(steps)
        },
        "error": None
    }


@tool_handler("add_trigger")
async def handle_add_trigger(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Ajoute un trigger à une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")
    trigger_type = arguments.get("trigger_type")
    config = arguments.get("config")

    if not all([automation_id, trigger_type, config]):
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameters: automation_id, trigger_type, config"
        }

    trigger_id = await crud.create_trigger(
        automation_id=automation_id,
        trigger_type=trigger_type,
        config=config
    )

    return {
        "success": True,
        "result": {"trigger_id": trigger_id},
        "error": None
    }


@tool_handler("test_automation")
async def handle_test_automation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute une automation avec des paramètres de test."""
    from app.core.services.automation import executor

    automation_id = arguments.get("automation_id")
    params = arguments.get("params", {})

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    result = await executor.execute_automation(
        automation_id=automation_id,
        params=params
    )

    return {
        "success": result["status"] == "success",
        "result": result,
        "error": result.get("error")
    }


@tool_handler("list_executions")
async def handle_list_executions(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste l'historique d'exécution d'une automation."""
    from app.database.crud import automations as crud

    automation_id = arguments.get("automation_id")
    limit = arguments.get("limit", 50)

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    executions = await crud.list_executions(automation_id, limit=limit)

    return {
        "success": True,
        "result": {
            "automation_id": automation_id,
            "executions": executions,
            "total": len(executions)
        },
        "error": None
    }


@tool_handler("get_execution")
async def handle_get_execution(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Récupère les détails d'une exécution."""
    from app.database.crud import automations as crud

    execution_id = arguments.get("execution_id")

    if not execution_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: execution_id"
        }

    execution = await crud.get_execution(execution_id)

    if not execution:
        return {
            "success": False,
            "result": None,
            "error": f"Execution {execution_id} not found"
        }

    return {
        "success": True,
        "result": execution,
        "error": None
    }


@tool_handler("cancel_execution")
async def handle_cancel_execution(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Annule une exécution en cours."""
    from app.database.crud import automations as crud

    execution_id = arguments.get("execution_id")

    if not execution_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: execution_id"
        }

    # Vérifier que l'execution existe et est en cours
    execution = await crud.get_execution(execution_id)
    if not execution:
        return {
            "success": False,
            "result": None,
            "error": f"Execution {execution_id} not found"
        }

    current_status = execution.get("status")
    if current_status not in ["running", "paused"]:
        return {
            "success": False,
            "result": None,
            "error": f"Cannot cancel execution with status '{current_status}'"
        }

    # Mettre à jour le statut
    success = await crud.update_execution_status(
        execution_id=execution_id,
        status="cancelled",
        error="Cancelled by user"
    )

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to cancel execution"
        }

    return {
        "success": True,
        "result": {
            "execution_id": execution_id,
            "status": "cancelled"
        },
        "error": None
    }


@tool_handler("update_workflow_step")
async def handle_update_workflow_step(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour un workflow step."""
    from app.database.crud import workflow_steps as step_crud

    step_id = arguments.get("step_id")

    if not step_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: step_id"
        }

    # Vérifier que le step existe
    step = await step_crud.get_workflow_step(step_id)
    if not step:
        return {
            "success": False,
            "result": None,
            "error": f"Workflow step {step_id} not found"
        }

    # Construire les updates
    updates = {}
    if arguments.get("step_order") is not None:
        updates["step_order"] = arguments.get("step_order")
    if arguments.get("step_name") is not None:
        updates["step_name"] = arguments.get("step_name")
    if arguments.get("step_type") is not None:
        updates["step_type"] = arguments.get("step_type")
    if arguments.get("step_subtype") is not None:
        updates["step_subtype"] = arguments.get("step_subtype")
    if arguments.get("config") is not None:
        updates["config"] = arguments.get("config")
    if arguments.get("run_condition") is not None:
        updates["run_condition"] = arguments.get("run_condition")
    if arguments.get("enabled") is not None:
        updates["enabled"] = arguments.get("enabled")

    if not updates:
        return {
            "success": False,
            "result": None,
            "error": "No fields to update"
        }

    success = await step_crud.update_workflow_step(step_id, **updates)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to update workflow step"
        }

    # Retourner le step mis à jour
    updated_step = await step_crud.get_workflow_step(step_id)

    return {
        "success": True,
        "result": updated_step,
        "error": None
    }


@tool_handler("delete_workflow_step")
async def handle_delete_workflow_step(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Supprime un workflow step."""
    from app.database.crud import workflow_steps as step_crud

    step_id = arguments.get("step_id")

    if not step_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: step_id"
        }

    # Vérifier que le step existe
    step = await step_crud.get_workflow_step(step_id)
    if not step:
        return {
            "success": False,
            "result": None,
            "error": f"Workflow step {step_id} not found"
        }

    success = await step_crud.delete_workflow_step(step_id)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to delete workflow step"
        }

    return {
        "success": True,
        "result": {"step_id": step_id, "deleted": True},
        "error": None
    }


@tool_handler("update_trigger")
async def handle_update_trigger(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour un trigger."""
    from app.database.crud import triggers as trigger_crud

    trigger_id = arguments.get("trigger_id")

    if not trigger_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: trigger_id"
        }

    # Vérifier que le trigger existe
    trigger = await trigger_crud.get_trigger(trigger_id)
    if not trigger:
        return {
            "success": False,
            "result": None,
            "error": f"Trigger {trigger_id} not found"
        }

    # Construire les updates
    updates = {}
    if arguments.get("trigger_type") is not None:
        updates["trigger_type"] = arguments.get("trigger_type")
    if arguments.get("config") is not None:
        updates["config"] = arguments.get("config")
    if arguments.get("enabled") is not None:
        updates["enabled"] = arguments.get("enabled")

    if not updates:
        return {
            "success": False,
            "result": None,
            "error": "No fields to update"
        }

    success = await trigger_crud.update_trigger(trigger_id, **updates)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to update trigger"
        }

    # Retourner le trigger mis à jour
    updated_trigger = await trigger_crud.get_trigger(trigger_id)

    return {
        "success": True,
        "result": updated_trigger,
        "error": None
    }


@tool_handler("delete_trigger")
async def handle_delete_trigger(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Supprime un trigger."""
    from app.database.crud import triggers as trigger_crud

    trigger_id = arguments.get("trigger_id")

    if not trigger_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: trigger_id"
        }

    # Vérifier que le trigger existe
    trigger = await trigger_crud.get_trigger(trigger_id)
    if not trigger:
        return {
            "success": False,
            "result": None,
            "error": f"Trigger {trigger_id} not found"
        }

    success = await trigger_crud.delete_trigger(trigger_id)

    if not success:
        return {
            "success": False,
            "result": None,
            "error": "Failed to delete trigger"
        }

    return {
        "success": True,
        "result": {"trigger_id": trigger_id, "deleted": True},
        "error": None
    }


@tool_handler("list_triggers")
async def handle_list_triggers(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste tous les triggers d'une automation."""
    from app.database.crud import triggers as trigger_crud

    automation_id = arguments.get("automation_id")

    if not automation_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: automation_id"
        }

    triggers = await trigger_crud.get_triggers(automation_id)

    return {
        "success": True,
        "result": {
            "automation_id": automation_id,
            "triggers": triggers,
            "total": len(triggers)
        },
        "error": None
    }
