from fastapi import APIRouter, Depends, status
from typing import List, Optional
from app.database.models import User
from app.api.v1.schemas.validations import (
    ValidationCreate,
    ValidationUpdate,
    ValidationResponse,
    ApproveValidationRequest,
    RejectValidationRequest,
    FeedbackValidationRequest
)
from app.core.services.validation.manager import ValidationManager
from app.core.utils.auth import get_current_user

router = APIRouter(prefix="/validations", tags=["validations"])

@router.post("", response_model=ValidationResponse, status_code=status.HTTP_201_CREATED)
async def create_validation(
    request: ValidationCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle demande de validation."""
    validation_id = await ValidationManager.create_validation(request, current_user.id)
    return await ValidationManager.get_validation(validation_id, current_user.id)

@router.get("", response_model=List[ValidationResponse])
async def list_validations(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Liste les validations de l'utilisateur avec filtre optionnel sur le statut."""
    return await ValidationManager.list_validations(current_user.id, status_filter)

@router.get("/{validation_id}", response_model=ValidationResponse)
async def get_validation(
    validation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère une validation par ID avec vérification ownership."""
    return await ValidationManager.get_validation(validation_id, current_user.id)

@router.patch("/{validation_id}/status", response_model=ValidationResponse)
async def update_validation_status(
    validation_id: str,
    request: ValidationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour le statut d'une validation avec validation de transition."""
    return await ValidationManager.update_status(
        validation_id=validation_id,
        user_id=current_user.id,
        new_status=request.status
    )


# ============================================================================
# ENDPOINTS POUR LE SYSTÈME DE VALIDATION DES TOOL CALLS
# ============================================================================

@router.post("/{validation_id}/approve")
async def approve_validation(
    validation_id: str,
    request: ApproveValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Approuve une validation et exécute le tool call.

    Side effects:
        - Exécute le tool via MCP
        - Crée des messages tool_call (executing, completed/failed)
        - Crée des logs
        - Si stream actif: injecte le résultat et reprend le stream automatiquement
        - Si stream inactif: relance génération en background
    """
    return await ValidationManager.approve(
        validation_id=validation_id,
        user_id=current_user.id,
        always_allow=request.always_allow
    )


@router.post("/{validation_id}/reject")
async def reject_validation(
    validation_id: str,
    request: RejectValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Rejette une validation.

    Side effects:
        - Update validation.status = 'rejected'
        - Crée message tool_call avec step='rejected'
        - Crée log
        - Annule toutes les autres validations pending du même chat (cascade)
        - Si stream actif: injecte le rejet et reprend le stream
    """
    return await ValidationManager.reject(
        validation_id=validation_id,
        user_id=current_user.id,
        reason=request.reason
    )


@router.post("/{validation_id}/feedback")
async def feedback_validation(
    validation_id: str,
    request: FeedbackValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Donne un feedback sur une validation.

    Le feedback sera transmis au LLM qui pourra alors décider de:
    - Re-call le tool avec des arguments modifiés
    - Annuler l'action
    - Demander des clarifications

    Side effects:
        - Update validation.status = 'feedback'
        - Crée message tool_call avec step='feedback_received'
        - Crée log
        - Si stream actif: injecte le feedback et reprend le stream
    """
    return await ValidationManager.feedback(
        validation_id=validation_id,
        user_id=current_user.id,
        feedback=request.feedback
    )

@router.get("/{validation_id}/logs")
async def get_validation_logs(
    validation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les logs d'action associés à une validation.

    Retourne l'historique des actions effectuées (approved, rejected, feedback)
    avec leurs détails (reason, feedback, timestamps).
    """
    return await ValidationManager.get_logs(validation_id, current_user.id)
