#!/usr/bin/env python3
# app/core/services/validation/manager.py
"""
Service manager pour les validations.

Orchestre la logique métier et délègue à ValidationService (existant) pour l'exécution.
Gère les validations de transitions, ownership, et injection dans le stream.
"""

from typing import List, Optional, Dict, Any
from app.core.services.base import BaseService
from app.core.validators.validation import ValidationValidator
from app.core.exceptions import ValidationError
from app.database import crud
from app.database.models import Validation, User
from app.api.v1.schemas.validations import ValidationCreate, ValidationResponse


class ValidationManager(BaseService):
    """Manager pour orchestrer les opérations sur les validations."""

    @staticmethod
    async def create_validation(dto: ValidationCreate, user_id: str) -> str:
        """
        Crée une nouvelle validation.

        Args:
            dto: Données de la validation (validées par Pydantic)
            user_id: ID de l'utilisateur créateur

        Returns:
            validation_id: ID de la validation créée

        Raises:
            ValidationError: Si les données sont invalides (déjà géré par Pydantic)
        """
        validation_id = await crud.create_validation(
            user_id=user_id,
            title=dto.title,
            description=dto.description,
            source=dto.source,
            process=dto.process,
            agent_id=dto.agent_id,
            status='pending'
        )
        return validation_id

    @staticmethod
    async def get_validation(validation_id: str, user_id: str) -> ValidationResponse:
        """
        Récupère une validation avec vérification ownership.

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur

        Returns:
            ValidationResponse

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
        """
        validation = await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )
        return ValidationResponse(**validation.to_dict())

    @staticmethod
    async def list_validations(
        user_id: str,
        status_filter: Optional[str] = None
    ) -> List[ValidationResponse]:
        """
        Liste les validations d'un utilisateur avec filtre optionnel sur le statut.

        Args:
            user_id: ID de l'utilisateur
            status_filter: Statut à filtrer (pending, approved, rejected, etc.)

        Returns:
            Liste de ValidationResponse
        """
        validations = await crud.list_validations_by_user(user_id, status_filter)
        return [
            ValidationResponse(**Validation.from_row(v).to_dict())
            for v in validations
        ]

    @staticmethod
    async def update_status(
        validation_id: str,
        user_id: str,
        new_status: str
    ) -> ValidationResponse:
        """
        Met à jour le statut d'une validation avec validation de transition.

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur
            new_status: Nouveau statut cible

        Returns:
            ValidationResponse mise à jour

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
            ValidationError: Si transition non autorisée
        """
        # 1. Vérifier ownership
        validation = await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )

        # 2. Vérifier transition valide
        await ValidationValidator.validate_status_transition(
            current_status=validation.status,
            new_status=new_status
        )

        # 3. Mettre à jour
        success = await crud.update_validation_status(validation_id, new_status)
        if not success:
            raise ValidationError("Failed to update validation status")

        # 4. Retourner validation mise à jour
        return await ValidationManager.get_validation(validation_id, user_id)

    @staticmethod
    async def approve(
        validation_id: str,
        user_id: str,
        always_allow: bool
    ) -> Dict[str, Any]:
        """
        Approuve une validation et exécute le tool call.

        Délègue l'exécution à ValidationService (existant).
        Gère l'injection dans le stream si actif, sinon lance une génération en background.

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur
            always_allow: Si True, auto-approuver ce tool pour les appels futurs

        Returns:
            Dict avec success, message, stream_active, tool_result, always_allow

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
            ValidationError: Si status != pending ou si exécution échoue
        """
        # 1. Vérifier ownership
        validation = await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )

        # 2. Vérifier status = pending
        await ValidationValidator.ensure_validation_pending(validation)

        # 3. Déléguer à ValidationService (existant, ne pas modifier)
        from app.core.utils.validation import validation_service
        result = await validation_service.approve_validation(
            validation_id=validation_id,
            always_allow=always_allow
        )

        if not result["success"]:
            raise ValidationError(
                result.get("error", "Failed to approve validation")
            )

        # 4. Gérer stream injection (garder logique existante)
        from app.core.services.llm.manager import stream_manager
        from config.logger import logger
        import asyncio

        stream_active = False

        if validation.chat_id:
            if stream_manager.is_stream_active(validation.chat_id):
                # Injecter le résultat dans le stream actif
                injected = await stream_manager.inject_validation_result(
                    chat_id=validation.chat_id,
                    validation_result={
                        "validation_id": validation_id,
                        "action": "approved",
                        "data": result["tool_result"]
                    }
                )

                if injected:
                    stream_active = True
                    logger.info(f"Validation {validation_id} approved and injected into active stream")

                    # Si session déconnectée, la supprimer maintenant (validation résolue)
                    session = stream_manager.get_session(validation.chat_id)
                    if session and session.disconnected_at:
                        logger.info(f"Validation resolved, cleaning up disconnected session {validation.chat_id}")
                        stream_manager.end_session(validation.chat_id)
                else:
                    logger.warning(f"Failed to inject validation {validation_id} into stream")
            else:
                # Pas de stream actif → relancer génération en background
                logger.info(f"No active stream, resuming generation in background for chat {validation.chat_id}")

                # Récupérer user pour background task
                user_row = await crud.get_user(user_id)
                current_user = User.from_row(user_row) if user_row else None

                # Lancer la génération en background (asyncio task)
                from app.core.services.llm.background_tasks import resume_generation_after_validation
                asyncio.create_task(
                    resume_generation_after_validation(
                        chat_id=validation.chat_id,
                        validation_id=validation_id,
                        tool_result=result["tool_result"],
                        user=current_user
                    )
                )

                stream_active = False  # Pas de stream frontend, mais génération en cours

        return {
            "success": True,
            "message": "Validation approved and tool executed",
            "stream_active": stream_active,
            "tool_result": result["tool_result"],
            "always_allow": always_allow
        }

    @staticmethod
    async def reject(
        validation_id: str,
        user_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """
        Rejette une validation.

        Délègue à ValidationService et gère:
        - Cascade: annule toutes les validations pending du même chat
        - Stream injection si actif

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur
            reason: Raison du rejet (optionnel)

        Returns:
            Dict avec success, message, stream_active

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
            ValidationError: Si status != pending ou si rejet échoue
        """
        # 1. Vérifier ownership
        validation = await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )

        # 2. Vérifier status = pending
        await ValidationValidator.ensure_validation_pending(validation)

        # 3. Déléguer à ValidationService
        from app.core.utils.validation import validation_service
        result = await validation_service.reject_validation(
            validation_id=validation_id,
            reason=reason
        )

        if not result["success"]:
            raise ValidationError(
                result.get("error", "Failed to reject validation")
            )

        # 4. Cascade: annuler toutes les autres validations pending du chat
        if validation.chat_id:
            from config.logger import logger
            cancelled_count = await crud.cancel_all_pending_validations(
                chat_id=validation.chat_id,
                reason="cascade_after_rejection"
            )
            logger.info(f"Cascade cancelled {cancelled_count} pending validations after rejecting {validation_id}")

        # 5. Gérer stream injection
        from app.core.services.llm.manager import stream_manager
        from config.logger import logger

        stream_active = False

        if validation.chat_id:
            if stream_manager.is_stream_active(validation.chat_id):
                injected = await stream_manager.inject_validation_result(
                    chat_id=validation.chat_id,
                    validation_result={
                        "validation_id": validation_id,
                        "action": "rejected",
                        "data": None
                    }
                )

                if injected:
                    stream_active = True
                    logger.info(f"Validation {validation_id} rejected and injected into active stream")

        return {
            "success": True,
            "message": "Validation rejected" if stream_active else "Validation rejected (stream closed)",
            "stream_active": stream_active
        }

    @staticmethod
    async def feedback(
        validation_id: str,
        user_id: str,
        feedback: str
    ) -> Dict[str, Any]:
        """
        Donne un feedback sur une validation.

        Le feedback est transmis au LLM qui décidera de l'action à prendre
        (re-call avec args modifiés, annulation, demande de clarifications, etc.).

        Délègue à ValidationService et gère stream injection.

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur
            feedback: Feedback utilisateur (déjà validé par Pydantic)

        Returns:
            Dict avec success, message, stream_active, feedback

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
            ValidationError: Si status != pending ou si feedback échoue
        """
        # 1. Vérifier ownership
        validation = await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )

        # 2. Vérifier status = pending
        await ValidationValidator.ensure_validation_pending(validation)

        # 3. Déléguer à ValidationService
        from app.core.utils.validation import validation_service
        result = await validation_service.feedback_validation(
            validation_id=validation_id,
            feedback=feedback
        )

        if not result["success"]:
            raise ValidationError(
                result.get("error", "Failed to submit feedback")
            )

        # 4. Gérer stream injection
        from app.core.services.llm.manager import stream_manager
        from config.logger import logger

        stream_active = False

        if validation.chat_id:
            if stream_manager.is_stream_active(validation.chat_id):
                injected = await stream_manager.inject_validation_result(
                    chat_id=validation.chat_id,
                    validation_result={
                        "validation_id": validation_id,
                        "action": "feedback",
                        "data": {"feedback": feedback}
                    }
                )

                if injected:
                    stream_active = True
                    logger.info(f"Feedback for validation {validation_id} injected into active stream")

        return {
            "success": True,
            "message": "Feedback submitted" if stream_active else "Feedback submitted (stream closed, send a new message to continue)",
            "stream_active": stream_active,
            "feedback": feedback
        }

    @staticmethod
    async def get_logs(validation_id: str, user_id: str) -> List[Dict]:
        """
        Récupère les logs d'action associés à une validation.

        Retourne l'historique des actions effectuées (approved, rejected, feedback)
        avec leurs détails (reason, feedback, timestamps).

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur

        Returns:
            Liste de logs

        Raises:
            NotFoundError: Si validation n'existe pas
            PermissionError: Si user n'est pas propriétaire
        """
        # 1. Vérifier ownership
        await ValidationValidator.check_validation_ownership(
            validation_id=validation_id,
            user_id=user_id
        )

        # 2. Récupérer logs
        logs = await crud.get_logs_by_validation_id(validation_id)
        return logs
