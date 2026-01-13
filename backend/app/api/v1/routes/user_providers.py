#!/usr/bin/env python3
# app/api/routes/user_providers.py

from fastapi import APIRouter, Depends, status, BackgroundTasks
from typing import List
from app.database import crud
from app.database.models import User
from app.api.v1.schemas import (
    UserProviderCreate,
    UserProviderUpdate,
    UserProviderResponse
)
from app.core.utils.auth import get_current_user
from config.logger import logger
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException

router = APIRouter(prefix="/providers", tags=["providers"])


async def _sync_models_background(provider_name: str):
    """
    Synchronise les modèles en arrière-plan après l'ajout d'un provider.

    Args:
        provider_name: Nom du provider (ex: 'openai', 'anthropic')
    """
    try:
        from app.core.services.llm.sync import model_sync_service
        logger.info(f"🔄 Starting background sync for provider: {provider_name}")
        report = await model_sync_service.sync_models_to_db(provider=provider_name)
        logger.info(
            f"✅ Models synced for {provider_name}: "
            f"{len(report['created'])} created, "
            f"{len(report['already_exists'])} already exists, "
            f"{len(report['errors'])} errors"
        )
    except Exception as e:
        logger.error(f"❌ Background sync failed for {provider_name}: {e}")

@router.post("", response_model=UserProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_user_provider(
    request: UserProviderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Active un provider LLM pour l'utilisateur connecté.
    """
    # Vérifier que le service existe
    service = await crud.get_service(request.service_id)
    if not service:
        raise NotFoundError("Service not found")

    # Vérifier que la clé API existe et appartient à l'utilisateur
    if request.api_key_id:
        api_key = await crud.get_api_key(request.api_key_id)
        if not api_key:
            raise NotFoundError("API key not found")
        if api_key.get('user_id') != current_user.id:
            raise PermissionError("API key does not belong to you")

    # Vérifier si le provider n'est pas déjà activé
    existing = await crud.get_user_provider_by_service(current_user.id, request.service_id)
    if existing:
        raise ValidationError(
            "Provider already configured. Use PATCH to update."
        )

    try:
        provider_id = await crud.create_user_provider(
            user_id=current_user.id,
            service_id=request.service_id,
            api_key_id=request.api_key_id,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(str(e))

    provider = await crud.get_user_provider(provider_id)
    if not provider:
        raise AppException("Failed to create user provider")

    # Synchroniser les modèles en arrière-plan
    if service and service.get('provider'):
        background_tasks.add_task(
            _sync_models_background,
            provider_name=service['provider']
        )
        logger.info(f"📋 Scheduled background sync for provider: {service['provider']}")

    return UserProviderResponse(**provider)

@router.get("", response_model=List[UserProviderResponse])
async def list_user_providers(
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les providers activés pour l'utilisateur connecté.
    """
    providers = await crud.list_user_providers(user_id=current_user.id)
    return [UserProviderResponse(**p) for p in providers]

@router.get("/{provider_id}", response_model=UserProviderResponse)
async def get_user_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère un provider par ID.
    """
    provider = await crud.get_user_provider(provider_id)
    if not provider:
        raise NotFoundError("Provider not found")

    # Vérifier que le provider appartient à l'utilisateur
    if provider['user_id'] != current_user.id:
        raise PermissionError("Access forbidden")

    return UserProviderResponse(**provider)

@router.patch("/{provider_id}", response_model=UserProviderResponse)
async def update_user_provider(
    provider_id: str,
    request: UserProviderUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour un provider (change la clé API ou active/désactive).
    """
    provider = await crud.get_user_provider(provider_id)
    if not provider:
        raise NotFoundError("Provider not found")

    # Vérifier que le provider appartient à l'utilisateur
    if provider['user_id'] != current_user.id:
        raise PermissionError("Access forbidden")

    # Vérifier que la nouvelle clé API appartient à l'utilisateur
    if request.api_key_id:
        api_key = await crud.get_api_key(request.api_key_id)
        if not api_key:
            raise NotFoundError("API key not found")
        if api_key.get('user_id') != current_user.id:
            raise PermissionError("API key does not belong to you")

    try:
        success = await crud.update_user_provider(
            provider_id=provider_id,
            api_key_id=request.api_key_id,
            enabled=request.enabled
        )
    except Exception as e:
        raise ValidationError(str(e))

    if not success:
        raise AppException("Failed to update provider")

    updated_provider = await crud.get_user_provider(provider_id)
    return UserProviderResponse(**updated_provider)

@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un provider pour l'utilisateur connecté.
    """
    provider = await crud.get_user_provider(provider_id)
    if not provider:
        raise NotFoundError("Provider not found")

    # Vérifier que le provider appartient à l'utilisateur
    if provider['user_id'] != current_user.id:
        raise PermissionError("Access forbidden")

    success = await crud.delete_user_provider(provider_id)
    if not success:
        raise AppException("Failed to delete provider")

    return None
