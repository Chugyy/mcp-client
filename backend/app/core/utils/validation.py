"""
Validation Service - Logique métier pour la validation des tool calls.

Ce service orchestre :
- La création de validations et messages tool_call
- La vérification des permissions (permission_level + cache)
- L'exécution des tools après validation
- La gestion du feedback utilisateur

Voir TOOL_VALIDATION_SYSTEM.md pour plus de détails.
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime
from config.logger import logger
from app.database import crud
from app.database.models import User, Validation
from app.core.services.mcp import clients as mcp_clients


class ValidationService:
    """Service de gestion des validations de tool calls."""

    async def should_execute_tool(
        self,
        user: User,
        agent_id: Optional[str],
        tool_name: str,
        server_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Détermine si un tool doit être exécuté directement ou nécessite validation.

        Args:
            user: Utilisateur demandant l'exécution
            agent_id: ID de l'agent (optionnel)
            tool_name: Nom du tool
            server_id: ID du serveur MCP

        Returns:
            (should_execute, reason)
            - (True, None) : Exécuter directement
            - (False, "validation_required") : Demander validation
            - (False, "permission_denied") : Bloquer complètement

        Note:
            Ordre de vérification :
            0. Internal tools (RAG) → toujours autorisés (lecture seule)
            1. permission_level du user
            2. Cache des autorisations (logs avec always_allow=true)
        """
        # 0. Exempter les internal tools (RAG) - pas besoin de validation (lecture seule)
        if server_id == "__internal__":
            logger.debug(f"Internal tool {tool_name} bypasses validation (read-only)")
            return (True, None)

        permission_level = getattr(user, 'permission_level', 'validation_required')

        # 1. Vérifier permission_level
        if permission_level == 'no_tools':
            logger.warning(f"User {user.id} has no_tools permission level")
            return (False, "permission_denied")

        if permission_level == 'full_auto':
            logger.debug(f"User {user.id} has full_auto permission, executing directly")
            return (True, None)

        # 2. Si validation_required, vérifier le cache
        if permission_level == 'validation_required':
            cached = await crud.check_tool_cache(
                user_id=user.id,
                tool_name=tool_name,
                server_id=server_id,
                agent_id=agent_id
            )

            if cached:
                logger.info(f"Tool {tool_name} found in cache for user {user.id}, executing directly")
                return (True, None)

            logger.debug(f"Tool {tool_name} not in cache, validation required")
            return (False, "validation_required")

        # Fallback (ne devrait jamais arriver)
        logger.warning(f"Unknown permission_level: {permission_level}, defaulting to validation_required")
        return (False, "validation_required")

    async def create_validation_request(
        self,
        user_id: str,
        chat_id: str,
        agent_id: Optional[str],
        tool_name: str,
        server_id: str,
        tool_call_id: str,
        arguments: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Crée une demande de validation et un message tool_call associé.

        Args:
            user_id: ID de l'utilisateur
            chat_id: ID du chat
            agent_id: ID de l'agent (optionnel)
            tool_name: Nom du tool
            server_id: ID du serveur MCP
            tool_call_id: ID du tool call (du provider LLM)
            arguments: Arguments du tool call

        Returns:
            tuple (validation_id, message_id)

        Side effects:
            - Crée une entrée dans la table validations
            - Crée un message avec role='tool_call', step='validation_requested'
        """
        # 1. Créer la validation
        validation_id = await crud.create_validation(
            user_id=user_id,
            title=f"Autorisation requise: {tool_name}",
            source="tool_call",
            process="llm_stream",
            agent_id=agent_id,
            description=f"Le LLM demande l'autorisation d'utiliser l'outil '{tool_name}'",
            status="pending"
        )

        # Mettre à jour avec les champs spécifiques aux tool calls
        # TODO: Ajouter fonction update_validation dans crud
        from app.database.db import get_connection
        conn = await get_connection()
        try:
            await conn.execute(
                """UPDATE validations
                   SET chat_id = $1, tool_name = $2, server_id = $3, tool_args = $4::jsonb, execution_id = $5
                   WHERE id = $6""",
                chat_id, tool_name, server_id, json.dumps(arguments), execution_id, validation_id
            )
        finally:
            await conn.close()

        # 2. Créer le message tool_call
        content = f"Demande d'autorisation pour utiliser l'outil : {tool_name}"

        metadata = {
            "step": "validation_requested",
            "validation_id": validation_id,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "server_id": server_id,
            "arguments": arguments,
            "status": "pending",
            "history": [
                {
                    "step": "validation_requested",
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "pending"
                }
            ]
        }

        logger.info(f"🟡 CREATING TOOL_CALL MESSAGE (without turn_info) | validation_id={validation_id} | tool_name={tool_name}")
        message_id = await crud.create_message(
            chat_id=chat_id,
            role="tool_call",
            content=content,
            metadata=metadata
        )

        logger.info(f"Validation request created: {validation_id} for tool {tool_name} | message_id={message_id}")

        return validation_id, message_id

    async def approve_validation(
        self,
        validation_id: str,
        always_allow: bool = False
    ) -> Dict[str, Any]:
        """
        Approuve une validation et exécute le tool.

        Args:
            validation_id: ID de la validation
            always_allow: Si True, ajoute au cache pour auto-approbation future

        Returns:
            {
                "success": bool,
                "validation_id": str,
                "tool_result": Any,
                "error": Optional[str]
            }

        Side effects:
            - Update validation.status = 'approved'
            - Exécute le tool via MCP
            - Update validation.tool_result
            - Crée message avec step='executing' puis step='completed'
            - Crée log type='tool_call'
            - Si always_allow=True, crée log avec data.always_allow=true
            - Crée log type='validation' avec action='approved'
        """
        # 1. Récupérer la validation
        validation_row = await crud.get_validation(validation_id)
        if not validation_row:
            return {"success": False, "error": "Validation not found"}

        validation = Validation.from_row(validation_row)

        if validation.status != 'pending':
            return {"success": False, "error": f"Validation already {validation.status}"}

        # 2. Update status
        await crud.update_validation_status(validation_id, 'approved')

        # 3. Récupérer le message tool_call original
        from app.database.crud import chats as crud_chats
        tool_call_message = await crud_chats.get_message_by_validation_id(validation_id)

        if not tool_call_message:
            logger.error(f"No tool_call message found for validation {validation_id}")
            return {"success": False, "error": "Tool call message not found"}

        # 4. Mettre à jour step → 'executing'
        history = tool_call_message.metadata.get("history", [])
        history.append({
            "step": "executing",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "approved"
        })

        await crud_chats.update_message_metadata(
            message_id=tool_call_message.id,
            metadata_updates={
                "step": "executing",
                "status": "approved",
                "history": history
            }
        )

        # 5. Exécuter le tool
        result = await mcp_clients.tool_call(
            server_id=validation.server_id,
            tool_name=validation.tool_name,
            arguments=validation.tool_args,
            user_id=validation.user_id
        )

        # 6. Sauvegarder le résultat dans la validation
        from app.database.db import get_connection
        conn = await get_connection()
        try:
            await conn.execute(
                """UPDATE validations
                   SET tool_result = $1::jsonb
                   WHERE id = $2""",
                json.dumps(result), validation_id
            )
        finally:
            await conn.close()

        # 7. Clear awaiting_validation_id dans le chat
        if validation.chat_id:
            await crud.set_validation_pending(validation.chat_id, None)

        # 8. Mettre à jour step → 'completed' ou 'failed'
        final_step = "completed" if result['success'] else "failed"
        history.append({
            "step": final_step,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        })

        await crud_chats.update_message_metadata(
            message_id=tool_call_message.id,
            metadata_updates={
                "step": final_step,
                "result": result,
                "history": history
            }
        )

        # 7. Créer log tool_call
        await crud.create_log(
            user_id=validation.user_id,
            log_type="tool_call",
            data={
                "tool_name": validation.tool_name,
                "server_id": validation.server_id,
                "args": validation.tool_args,
                "result": result,
                "status": "executed" if result['success'] else "error",
                "always_allow": always_allow
            },
            agent_id=validation.agent_id,
            chat_id=validation.chat_id
        )

        # 8. Créer log validation
        await crud.create_log(
            user_id=validation.user_id,
            log_type="validation",
            data={
                "validation_id": validation_id,
                "action": "approved",
                "tool_name": validation.tool_name,
                "always_allow": always_allow
            },
            agent_id=validation.agent_id,
            chat_id=validation.chat_id
        )

        logger.info(
            f"Validation approved: {validation_id}, "
            f"tool={validation.tool_name}, "
            f"success={result['success']}, "
            f"always_allow={always_allow}"
        )

        # PHASE 3D : Auto-resume execution si validation liée à automation
        if validation.execution_id:
            logger.info(f"🔗 Validation {validation_id} linked to execution {validation.execution_id}")

            # Vérifier si toutes validations de cette execution sont traitées
            all_validations = await crud.get_validations_by_execution(validation.execution_id)
            pending = [v for v in all_validations if v.get('status') == 'pending' and v.get('id') != validation_id]

            if not pending:
                logger.info(f"✅ All validations completed for execution {validation.execution_id}, resuming...")

                # Reprendre l'execution automatiquement
                from app.core.services.automation.executor import resume_execution
                resume_result = await resume_execution(validation.execution_id)

                if resume_result.get("status") == "success":
                    logger.info(f"✅ Execution {validation.execution_id} resumed and completed")
                else:
                    logger.error(f"❌ Failed to resume execution {validation.execution_id}: {resume_result.get('error')}")
            else:
                logger.info(f"⏳ {len(pending)} validation(s) still pending for execution {validation.execution_id}")

        return {
            "success": True,
            "validation_id": validation_id,
            "tool_result": result,
            "error": None
        }

    async def reject_validation(
        self,
        validation_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rejette une validation.

        Args:
            validation_id: ID de la validation
            reason: Raison du refus (optionnel)

        Returns:
            {"success": bool, "error": Optional[str]}

        Side effects:
            - Update validation.status = 'rejected'
            - Crée message avec step='rejected'
            - Crée log type='validation' avec action='rejected'
        """
        # 1. Récupérer la validation
        validation_row = await crud.get_validation(validation_id)
        if not validation_row:
            return {"success": False, "error": "Validation not found"}

        validation = Validation.from_row(validation_row)

        if validation.status != 'pending':
            return {"success": False, "error": f"Validation already {validation.status}"}

        # 2. Update status
        await crud.update_validation_status(validation_id, 'rejected')

        # 3. Récupérer le message tool_call original
        from app.database.crud import chats as crud_chats
        tool_call_message = await crud_chats.get_message_by_validation_id(validation_id)

        if tool_call_message:
            # Mettre à jour le message existant
            history = tool_call_message.metadata.get("history", [])
            history.append({
                "step": "rejected",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason
            })

            await crud_chats.update_message_metadata(
                message_id=tool_call_message.id,
                metadata_updates={
                    "step": "rejected",
                    "status": "rejected",
                    "history": history
                }
            )

        # 4. Créer log validation
        await crud.create_log(
            user_id=validation.user_id,
            log_type="validation",
            data={
                "validation_id": validation_id,
                "action": "rejected",
                "tool_name": validation.tool_name,
                "reason": reason
            },
            agent_id=validation.agent_id,
            chat_id=validation.chat_id
        )

        logger.info(f"Validation rejected: {validation_id}, tool={validation.tool_name}")

        return {"success": True, "error": None}

    async def feedback_validation(
        self,
        validation_id: str,
        feedback: str
    ) -> Dict[str, Any]:
        """
        Ajoute un feedback utilisateur sur une validation.

        Args:
            validation_id: ID de la validation
            feedback: Feedback de l'utilisateur

        Returns:
            {"success": bool, "error": Optional[str]}

        Side effects:
            - Update validation.status = 'feedback'
            - Crée message avec step='feedback_received'
            - Crée log type='validation' avec action='feedback'

        Note:
            Le feedback sera utilisé par le LLM pour décider de continuer/modifier/annuler.
            Le stream doit reprendre avec le feedback ajouté au contexte.
        """
        # 1. Récupérer la validation
        validation_row = await crud.get_validation(validation_id)
        if not validation_row:
            return {"success": False, "error": "Validation not found"}

        validation = Validation.from_row(validation_row)

        if validation.status != 'pending':
            return {"success": False, "error": f"Validation already {validation.status}"}

        # 2. Update status
        await crud.update_validation_status(validation_id, 'feedback')

        # 3. Créer message "feedback_received"
        await crud.create_message(
            chat_id=validation.chat_id,
            role="tool_call",
            content=f"Feedback reçu : {feedback}",
            metadata={
                "step": "feedback_received",
                "validation_id": validation_id,
                "tool_name": validation.tool_name,
                "server_id": validation.server_id,
                "arguments": validation.tool_args,
                "user_feedback": feedback
            }
        )

        # 4. Créer log validation
        await crud.create_log(
            user_id=validation.user_id,
            log_type="validation",
            data={
                "validation_id": validation_id,
                "action": "feedback",
                "tool_name": validation.tool_name,
                "feedback": feedback
            },
            agent_id=validation.agent_id,
            chat_id=validation.chat_id
        )

        logger.info(f"Feedback received for validation: {validation_id}")

        return {"success": True, "error": None}


# Instance globale
validation_service = ValidationService()
