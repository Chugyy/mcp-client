# app/api/routes/models.py
"""Endpoints pour gérer les modèles LLM (API providers + DB)."""

from fastapi import APIRouter, Depends, Query, status
from typing import Dict, List, Any, Optional
from app.database.models import User
from app.database import crud
from app.api.v1.schemas import ModelCreate, ModelUpdate, ModelResponse
from app.core.utils.auth import get_current_user
from app.core.services.llm.gateway import llm_gateway
from app.core.services.llm.sync import model_sync_service
from config.logger import logger
from app.core.exceptions import ValidationError, NotFoundError, AppException

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/providers", response_model=Dict[str, List[Dict[str, Any]]])
async def list_models_from_providers(
    provider: Optional[str] = Query(None, description="Provider spécifique (openai, anthropic) ou None pour tous"),
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les modèles LLM disponibles directement depuis les APIs des providers.

    Returns:
        Dict avec les modèles groupés par provider:
        {
            "openai": [{"id": "gpt-4o", "created": ...}, ...],
            "anthropic": [{"id": "claude-sonnet-4-5-20250929", ...}, ...]
        }
    """
    try:
        models = await llm_gateway.list_models(provider=provider)

        if not models:
            raise AppException(
                "No LLM providers are configured. Check API keys."
            )

        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise AppException(
            f"Failed to list models: {str(e)}"
        )

@router.post("/sync", response_model=Dict[str, Any])
async def sync_models_from_providers(
    provider: Optional[str] = Query(None, description="Provider spécifique (openai, anthropic) ou None pour tous"),
    current_user: User = Depends(get_current_user)
):
    """
    Synchronise les modèles depuis les providers vers la base de données.

    Returns:
        Rapport de synchronisation avec les modèles créés, existants et erreurs.
    """
    try:
        report = await model_sync_service.sync_models_to_db(provider=provider)
        return report
    except Exception as e:
        logger.error(f"Error syncing models: {e}")
        raise AppException(
            f"Failed to sync models: {str(e)}"
        )

@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    request: ModelCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crée un nouveau modèle LLM en base de données.
    """
    # Vérifier que le service existe
    service = await crud.get_service(request.service_id)
    if not service:
        raise NotFoundError("Service not found")

    try:
        model_id = await crud.create_model(
            service_id=request.service_id,
            model_name=request.model_name,
            display_name=request.display_name,
            description=request.description,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(str(e))

    model = await crud.get_model(model_id)
    if not model:
        raise AppException("Failed to create model")

    return ModelResponse(**model)

@router.get("")
async def list_models_from_db(
    current_user: User = Depends(get_current_user)
):
    """
    Liste uniquement les modèles disponibles pour l'utilisateur connecté.
    Filtre automatiquement par providers activés avec clé API configurée.
    """
    models = await crud.list_models_for_user(user_id=current_user.id)
    return models

@router.get("/with-service")
async def list_models_with_service_info(
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les modèles actifs avec leurs informations de service (JOIN).
    """
    models = await crud.list_models_with_service()
    return models

@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère un modèle par ID.
    """
    model = await crud.get_model(model_id)
    if not model:
        raise NotFoundError("Model not found")

    return ModelResponse(**model)

@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    request: ModelUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour un modèle.
    """
    model = await crud.get_model(model_id)
    if not model:
        raise NotFoundError("Model not found")

    try:
        success = await crud.update_model(
            model_id=model_id,
            model_name=request.model_name,
            display_name=request.display_name,
            description=request.description,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(str(e))

    if not success:
        raise AppException("Failed to update model")

    updated_model = await crud.get_model(model_id)
    return ModelResponse(**updated_model)

@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un modèle.
    """
    model = await crud.get_model(model_id)
    if not model:
        raise NotFoundError("Model not found")

    success = await crud.delete_model(model_id)
    if not success:
        raise AppException("Failed to delete model")

    return None
