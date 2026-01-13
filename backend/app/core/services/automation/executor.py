"""
Moteur d'exécution des workflows d'automation.

Ce module implémente l'exécution de workflows composés de steps (actions, contrôles).
Gère le cycle de vie complet : exécution, logging, gestion d'erreurs.
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from config.logger import logger
from app.core.services.automation.templates import (
    resolve_template,
    resolve_all_templates,
    get_nested_value,
    evaluate_condition
)


# ============================
# POINT D'ENTRÉE PRINCIPAL
# ============================

async def execute_automation(
    automation_id: str,
    trigger_id: Optional[str] = None,
    params: Optional[Dict] = None
) -> Dict:
    """
    Point d'entrée pour exécuter une automation complète.

    Args:
        automation_id: ID de l'automation à exécuter
        trigger_id: ID du trigger (webhook, cronjob, etc.) optionnel
        params: Paramètres fournis par le trigger

    Returns:
        {
            "execution_id": str,
            "status": "success" | "failed",
            "result": Dict (contexte final si succès),
            "error": str (si erreur)
        }
    """
    from app.database import crud

    try:
        # 1. Charger l'automation
        automation = await crud.get_automation(automation_id)
        if not automation:
            return {
                "execution_id": None,
                "status": "failed",
                "result": None,
                "error": f"Automation {automation_id} not found"
            }

        # 2. Vérifier que l'automation est activée
        if not automation.get("enabled", False):
            return {
                "execution_id": None,
                "status": "failed",
                "result": None,
                "error": f"Automation {automation_id} is disabled"
            }

        # 3. Créer une execution en BDD (status='running')
        execution_id = await crud.create_execution(
            automation_id=automation_id,
            user_id=automation.get("user_id"),
            trigger_id=trigger_id,
            status="running",
            input_params=params
        )

        logger.info(f"Starting automation execution: {execution_id}")

        # 4. Charger les steps (ORDER BY step_order)
        steps = await crud.get_workflow_steps(automation_id)

        if not steps:
            await crud.update_execution_status(
                execution_id=execution_id,
                status="failed",
                error="No workflow steps found"
            )
            return {
                "execution_id": execution_id,
                "status": "failed",
                "result": None,
                "error": "No workflow steps found"
            }

        # 5. Construire le contexte initial
        context = {
            "trigger": params or {},
            "automation": {
                "id": automation_id,
                "name": automation.get("name"),
                "user_id": automation.get("user_id")
            },
            "variables": {},  # Variables partagées entre steps
            "loop": {}  # État des boucles
        }

        # 6. Exécuter le workflow
        result_context = await execute_workflow(
            execution_id=execution_id,
            automation_id=automation_id,
            steps=steps,
            context=context,
            permission_level=automation.get("permission_level", "validation_required")
        )

        # 7. Marquer comme succès
        await crud.update_execution_status(
            execution_id=execution_id,
            status="success",
            result=result_context
        )

        logger.info(f"Automation execution completed: {execution_id}")

        return {
            "execution_id": execution_id,
            "status": "success",
            "result": result_context,
            "error": None
        }

    except Exception as e:
        logger.error(f"Automation execution failed: {e}", exc_info=True)

        # Marquer comme failed si execution_id existe
        if 'execution_id' in locals() and execution_id:
            await crud.update_execution_status(
                execution_id=execution_id,
                status="failed",
                error=str(e)
            )

        return {
            "execution_id": locals().get('execution_id'),
            "status": "failed",
            "result": None,
            "error": str(e)
        }


# ============================
# EXÉCUTION DU WORKFLOW
# ============================

async def execute_workflow(
    execution_id: str,
    automation_id: str,
    steps: List[Dict],
    context: Dict,
    permission_level: str,
    start_index: int = 0
) -> Dict:
    """
    Exécute un workflow step par step avec gestion du control flow.

    Args:
        execution_id: ID de l'execution en cours
        automation_id: ID de l'automation
        steps: Liste des steps triés par step_order
        context: Contexte partagé entre les steps
        permission_level: Niveau de permission (full_auto, validation_required, no_tools)
        start_index: Index du step par lequel commencer (pour resume)

    Returns:
        Context final après exécution de tous les steps
    """
    current_index = start_index

    while current_index < len(steps):
        step = steps[current_index]
        step_id = step.get("id")
        step_order = step.get("step_order")
        step_type = step.get("step_type")
        step_subtype = step.get("step_subtype")
        run_condition = step.get("run_condition")

        logger.debug(f"Executing step {step_order}: {step_type}/{step_subtype}")

        # Vérifier la condition d'exécution
        if run_condition:
            should_run = evaluate_condition(run_condition, context)
            if not should_run:
                logger.debug(f"Step {step_order} skipped (condition false)")
                await log_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    status="skipped",
                    result={"reason": "condition_false"},
                    error=None,
                    duration_ms=0
                )
                current_index += 1
                continue

        # Exécuter le step
        start_time = asyncio.get_event_loop().time()

        try:
            if step_type == "action":
                # Injecter current_index dans le contexte pour sauvegarde état
                context["__current_step_index__"] = current_index

                result = await execute_action(step, context, permission_level)

                # Stocker le résultat dans le contexte
                context[f"step_{step_order}"] = {"result": result}

                # Nettoyer l'index temporaire
                context.pop("__current_step_index__", None)

                # Logger le succès
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                await log_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    status="success",
                    result=result,
                    error=None,
                    duration_ms=duration_ms
                )

                current_index += 1

            elif step_type == "control":
                next_index = await execute_control(
                    step, context, steps, execution_id
                )

                # Logger le succès
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                await log_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    status="success",
                    result={"next_index": next_index},
                    error=None,
                    duration_ms=duration_ms
                )

                # Gérer le saut d'index
                if next_index is not None:
                    current_index = next_index
                else:
                    current_index += 1

            else:
                raise ValueError(f"Unknown step_type: {step_type}")

        except Exception as e:
            # Cas spécial : ValidationPendingException (automation en pause)
            from app.core.services.llm.gateway import ValidationPendingException
            if isinstance(e, ValidationPendingException):
                logger.info(f"⏸️ Execution paused at step {step_order}, awaiting validation {e.validation_id}")
                # L'état a déjà été sauvegardé en Phase 3B
                # Sortir proprement du workflow
                return context

            logger.error(f"Step {step_order} failed: {e}", exc_info=True)

            # Logger l'erreur
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            await log_step(
                execution_id=execution_id,
                step_id=step_id,
                status="failed",
                result=None,
                error=str(e),
                duration_ms=duration_ms
            )

            # Propager l'erreur
            raise

    return context


async def resume_execution(execution_id: str) -> Dict:
    """
    Reprend une execution mise en pause pour validation.

    Args:
        execution_id: ID de l'execution à reprendre

    Returns:
        {
            "execution_id": str,
            "status": "success" | "failed",
            "result": Dict (contexte final si succès),
            "error": str (si erreur)
        }
    """
    from app.database import crud

    try:
        # 1. Charger l'execution
        execution = await crud.get_execution(execution_id)
        if not execution:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "result": None,
                "error": f"Execution {execution_id} not found"
            }

        # 2. Vérifier que l'execution est en pause
        if execution.get("status") != "paused":
            return {
                "execution_id": execution_id,
                "status": "failed",
                "result": None,
                "error": f"Execution {execution_id} is not paused (status={execution.get('status')})"
            }

        # 3. Restaurer l'état
        execution_state = execution.get("execution_state")
        if not execution_state:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "result": None,
                "error": "Execution state not found"
            }

        context = execution_state.get("context", {})
        current_index = execution_state.get("current_index", 0)

        logger.info(f"▶️ Resuming execution {execution_id} from step index {current_index}")

        # 4. Mettre à jour l'execution
        await crud.update_execution(
            execution_id=execution_id,
            data={
                "status": "running",
                "resumed_at": "NOW()"
            }
        )

        # 5. Charger les steps
        automation_id = execution.get("automation_id")
        steps = await crud.get_workflow_steps(automation_id)

        if not steps:
            await crud.update_execution_status(
                execution_id=execution_id,
                status="failed",
                error="No workflow steps found"
            )
            return {
                "execution_id": execution_id,
                "status": "failed",
                "result": None,
                "error": "No workflow steps found"
            }

        # 6. Récupérer permission_level de l'automation
        automation = await crud.get_automation(automation_id)
        permission_level = automation.get("permission_level", "validation_required")

        # 7. Reprendre l'exécution depuis current_index
        result = await execute_workflow(
            execution_id=execution_id,
            automation_id=automation_id,
            steps=steps,
            context=context,
            permission_level=permission_level,
            start_index=current_index
        )

        # 8. Marquer comme succès
        await crud.update_execution_status(
            execution_id=execution_id,
            status="success",
            output_data=result
        )

        logger.info(f"✅ Execution {execution_id} resumed and completed successfully")

        return {
            "execution_id": execution_id,
            "status": "success",
            "result": result,
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to resume execution {execution_id}: {e}", exc_info=True)

        # Marquer l'execution comme failed
        try:
            await crud.update_execution_status(
                execution_id=execution_id,
                status="failed",
                error=str(e)
            )
        except:
            pass

        return {
            "execution_id": execution_id,
            "status": "failed",
            "result": None,
            "error": str(e)
        }


# ============================
# EXÉCUTION DES ACTIONS
# ============================

async def execute_action(
    step: Dict,
    context: Dict,
    permission_level: str
) -> Any:
    """
    Exécute une action (mcp_call, ai_agent, internal_tool).

    Args:
        step: Dictionnaire du step à exécuter
        context: Contexte actuel
        permission_level: Niveau de permission

    Returns:
        Résultat de l'action
    """
    step_subtype = step.get("step_subtype")
    config = step.get("config", {})

    # Résoudre les templates dans la config (ex: {{trigger.user_id}})
    resolved_config = resolve_all_templates(config, context)

    if step_subtype == "mcp_call":
        # Appel d'un tool MCP
        from app.core.services.mcp.clients import execute_tool

        server_id = resolved_config.get("server_id")
        tool_name = resolved_config.get("tool_name")
        # Après migration 017: seule la clé "arguments" est utilisée
        arguments = resolved_config.get("arguments", {})

        logger.debug(f"MCP call - tool: {tool_name}, server: {server_id}, arguments: {arguments}")

        if not server_id or not tool_name:
            raise ValueError("mcp_call requires server_id and tool_name")

        if not arguments:
            raise ValueError(f"mcp_call requires non-empty arguments for tool {tool_name}")

        # Récupérer le user_id depuis le contexte pour les serveurs internes
        user_id = context.get("automation", {}).get("user_id")

        result = await execute_tool(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id
        )

        if not result.get("success"):
            raise Exception(f"MCP tool failed: {result.get('error')}")

        return result.get("result")

    elif step_subtype == "ai_action":
        # Appel simple d'un agent avec un prompt (version simplifiée)
        agent_id = resolved_config.get("agent_id")
        base_prompt = resolved_config.get("prompt")

        if not agent_id or not base_prompt:
            raise ValueError("ai_action requires agent_id and prompt")

        # Récupérer l'agent
        from app.database import crud
        agent = await crud.get_agent(agent_id)

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Construire le contexte enrichi des steps précédents
        context_summary = []
        for key, value in context.items():
            if key.startswith("step_"):
                context_summary.append(f"{key}: {json.dumps(value, indent=2)}")

        # Injecter le contexte dans le prompt si disponible
        if context_summary:
            enriched_prompt = f"""Context from previous steps:
{chr(10).join(context_summary)}

User request:
{base_prompt}"""
        else:
            enriched_prompt = base_prompt

        # Charger les tools MCP pour cet agent
        from app.core.services.llm.utils.tools import build_tools_for_agent
        tools = await build_tools_for_agent(
            agent_id=agent_id,
            user_id=agent.get("user_id")
        )

        # Appeler le LLM avec le system prompt de l'agent
        from app.core.services.llm.gateway import llm_gateway

        model = agent.get("model", "gpt-4o-mini")
        system_prompt = agent.get("system_prompt")

        messages = [{"role": "user", "content": enriched_prompt}]

        response_text = ""

        # Créer un objet user minimal pour passer le user_id
        # Le user_id provient du contexte de l'automation
        logger.info(f"🔍 [Automation Executor] Context complet: {context}")
        automation_user_id = context.get("automation", {}).get("user_id")
        logger.info(f"🔍 [Automation Executor] User ID extrait du contexte: {automation_user_id}")

        user_obj = None
        if automation_user_id:
            # Créer un objet simple avec l'attribut id
            from types import SimpleNamespace
            user_obj = SimpleNamespace(id=automation_user_id)
            logger.info(f"✅ [Automation Executor] User object créé avec id={automation_user_id}")
        else:
            logger.warning("⚠️  [Automation Executor] Aucun user_id trouvé dans le contexte")

        # PHASE 3B : Sauvegarder l'état AVANT d'appeler le LLM si validation possible
        if tools and permission_level == "validation_required":
            logger.info(f"⏸️ [Automation Executor] Sauvegarde préventive de l'état (validation possible)")
            await crud.update_execution(
                execution_id=execution_id,
                data={
                    "execution_state": {
                        "context": context,
                        "current_index": context.get("__current_step_index__", 0)
                    },
                    "status": "paused",
                    "paused_at": "NOW()"
                }
            )

        # Utiliser stream_with_tools si des tools sont disponibles
        if tools:
            async for chunk in llm_gateway.stream_with_tools(
                messages=messages,
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                api_key_id="admin",
                agent_id=agent_id,
                user=user_obj,
                temperature=0.7,
                max_tokens=2000,
                execution_id=execution_id
            ):
                response_text += chunk
        else:
            async for chunk in llm_gateway.stream(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                api_key_id="admin",
                temperature=0.7,
                max_tokens=2000
            ):
                response_text += chunk

        return {"response": response_text}

    elif step_subtype == "ai_agent":
        # Appel d'un agent LLM (version complète avec messages custom)
        from app.core.services.llm.gateway import llm_gateway

        model = resolved_config.get("model", "gpt-4o-mini")
        messages = resolved_config.get("messages", [])
        system_prompt = resolved_config.get("system_prompt")
        temperature = resolved_config.get("temperature", 0.7)
        max_tokens = resolved_config.get("max_tokens", 2000)

        if not messages:
            raise ValueError("ai_agent requires messages")

        # Pour le MVP, on utilise une approche simple (non-stream)
        response_text = ""
        async for chunk in llm_gateway.stream(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            api_key_id="admin",
            temperature=temperature,
            max_tokens=max_tokens
        ):
            response_text += chunk

        return {"response": response_text}

    elif step_subtype == "internal_tool":
        # Appel d'un tool interne
        from app.core.system import handler
        # Import des handlers pour auto-registration
        from app.core.system import handlers  # noqa: F401
        execute_internal = handler.execute

        tool_name = resolved_config.get("tool_name")
        arguments = resolved_config.get("arguments", {})

        if not tool_name:
            raise ValueError("internal_tool requires tool_name")

        result = await execute_internal(tool_name, arguments)

        if not result.get("success"):
            raise Exception(f"Internal tool failed: {result.get('error')}")

        return result.get("result")

    else:
        raise ValueError(f"Unknown action subtype: {step_subtype}")


# ============================
# EXÉCUTION DES CONTRÔLES
# ============================

async def execute_control(
    step: Dict,
    context: Dict,
    steps: List[Dict],
    execution_id: str
) -> Optional[int]:
    """
    Exécute un control flow (condition, loop, delay).

    Args:
        step: Step de contrôle
        context: Contexte actuel
        steps: Liste de tous les steps
        execution_id: ID de l'execution

    Returns:
        Index du prochain step à exécuter, ou None pour continuer normalement
    """
    step_subtype = step.get("step_subtype")
    config = step.get("config", {})

    if step_subtype == "condition":
        # Évaluer une condition et sauter si nécessaire
        expression = config.get("expression")
        target_step = config.get("target_step")  # step_order où sauter
        action_on_true = config.get("action", "jump")  # "jump", "continue", "stop"

        if not expression:
            raise ValueError("condition requires expression")

        is_true = evaluate_condition(expression, context)

        if is_true:
            if action_on_true == "jump" and target_step is not None:
                # Trouver l'index du step cible
                target_index = next(
                    (i for i, s in enumerate(steps) if s.get("step_order") == target_step),
                    None
                )
                if target_index is None:
                    raise ValueError(f"Target step {target_step} not found")
                return target_index

            elif action_on_true == "stop":
                # Arrêter l'exécution
                return len(steps)

            else:
                # Continue normalement
                return None
        else:
            # Condition fausse, continuer normalement
            return None

    elif step_subtype == "loop":
        # Boucler sur une liste
        loop_list = config.get("list")  # Chemin dans le contexte (ex: "trigger.items") ou liste directe
        loop_var_name = config.get("variable", "item")
        loop_steps_orders = config.get("loop_steps", [])  # Liste des step_order à répéter

        if loop_list is None or not loop_steps_orders:
            raise ValueError("loop requires list and loop_steps")

        # Résoudre la liste depuis le contexte (ou utiliser directement si c'est déjà une liste)
        if isinstance(loop_list, list):
            items = loop_list
        else:
            items = resolve_template(loop_list, context)

        if not isinstance(items, list):
            raise ValueError(f"Loop list must be an array, got: {type(items)}")

        # Trouver les steps à boucler
        loop_step_indices = [
            i for i, s in enumerate(steps) if s.get("step_order") in loop_steps_orders
        ]

        if not loop_step_indices:
            raise ValueError(f"Loop steps not found: {loop_steps_orders}")

        # Itérer sur chaque item
        for index, item in enumerate(items):
            # Mettre à jour le contexte de boucle
            context["loop"][loop_var_name] = item
            context["loop"]["index"] = index
            context["loop"]["total"] = len(items)

            # Exécuter chaque step de la boucle
            for step_index in loop_step_indices:
                loop_step = steps[step_index]

                # Exécuter selon le type
                if loop_step.get("step_type") == "action":
                    result = await execute_action(
                        loop_step,
                        context,
                        config.get("permission_level", "validation_required")
                    )
                    context[f"step_{loop_step.get('step_order')}"] = {"result": result}

        # Nettoyer le contexte de boucle
        context["loop"].pop(loop_var_name, None)
        context["loop"].pop("index", None)
        context["loop"].pop("total", None)

        # Retourner l'index après le dernier step de la boucle
        return max(loop_step_indices) + 1

    elif step_subtype == "delay":
        # Attendre un certain temps
        duration_seconds = config.get("duration_seconds", 1)

        await asyncio.sleep(duration_seconds)

        return None

    else:
        raise ValueError(f"Unknown control subtype: {step_subtype}")


# ============================
# LOGGING DES STEPS
# ============================

async def log_step(
    execution_id: str,
    step_id: str,
    status: str,
    result: Optional[Dict],
    error: Optional[str],
    duration_ms: int
):
    """
    Enregistre le log d'exécution d'un step.

    Args:
        execution_id: ID de l'execution
        step_id: ID du step
        status: "success" | "failed" | "skipped"
        result: Résultat du step (si succès)
        error: Message d'erreur (si échec)
        duration_ms: Durée d'exécution en millisecondes
    """
    from app.database import crud

    await crud.create_step_log(
        execution_id=execution_id,
        step_id=step_id,
        status=status,
        result=result,
        error=error,
        duration_ms=duration_ms
    )
