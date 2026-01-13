from fastapi import APIRouter, Depends, status
from typing import List
from app.database import crud
from app.database.models import User, ApiKey
from app.api.v1.schemas import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyResponseWithValue
)
from app.core.utils.auth import get_current_user
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

@router.post("", response_model=ApiKeyResponseWithValue, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crée une nouvelle clé API chiffrée pour l'utilisateur connecté.
    La valeur en clair est retournée uniquement à la création.
    """
    # Vérifier que le service existe
    service = await crud.get_service(request.service_id)
    if not service:
        raise NotFoundError("Service not found")

    try:
        key_id = await crud.create_api_key(
            plain_value=request.plain_value,
            user_id=current_user.id,
            service_id=request.service_id
        )
    except ValueError as e:
        raise ValidationError(str(e))

    api_key = await crud.get_api_key(key_id)
    if not api_key:
        raise AppException("Failed to create API key")

    # Retourner la clé avec la valeur en clair uniquement à la création
    return ApiKeyResponseWithValue(
        id=api_key['id'],
        plain_value=request.plain_value,
        service_id=api_key['service_id'],
        created_at=api_key['created_at'],
        updated_at=api_key['updated_at']
    )

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user)
):
    """Liste toutes les clés API de l'utilisateur connecté (sans dévoiler les valeurs)."""
    api_keys = await crud.list_api_keys(user_id=current_user.id)
    return [
        ApiKeyResponse(
            id=k['id'],
            service_id=k.get('service_id'),
            created_at=k['created_at'],
            updated_at=k['updated_at']
        )
        for k in api_keys
    ]

@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère une clé API par ID (sans dévoiler la valeur)."""
    api_key = await crud.get_api_key(key_id)
    if not api_key:
        raise NotFoundError("API key not found")

    # Vérifier que la clé appartient à l'utilisateur
    if api_key.get('user_id') != current_user.id:
        raise PermissionError("Access forbidden")

    return ApiKeyResponse(
        id=api_key['id'],
        service_id=api_key.get('service_id'),
        created_at=api_key['created_at'],
        updated_at=api_key['updated_at']
    )

@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: str,
    request: ApiKeyUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour une clé API (rotation de clé)."""
    api_key = await crud.get_api_key(key_id)
    if not api_key:
        raise NotFoundError("API key not found")

    # Vérifier que la clé appartient à l'utilisateur
    if api_key.get('user_id') != current_user.id:
        raise PermissionError("Access forbidden")

    try:
        success = await crud.update_api_key(
            key_id=key_id,
            plain_value=request.plain_value
        )
    except ValueError as e:
        raise ValidationError(str(e))

    if not success:
        raise AppException("Failed to update API key")

    updated_key = await crud.get_api_key(key_id)
    return ApiKeyResponse(
        id=updated_key['id'],
        service_id=updated_key.get('service_id'),
        created_at=updated_key['created_at'],
        updated_at=updated_key['updated_at']
    )

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
):
    """Supprime une clé API."""
    api_key = await crud.get_api_key(key_id)
    if not api_key:
        raise NotFoundError("API key not found")

    # Vérifier que la clé appartient à l'utilisateur
    if api_key.get('user_id') != current_user.id:
        raise PermissionError("Access forbidden")

    success = await crud.delete_api_key(key_id)
    if not success:
        raise AppException("Failed to delete API key")

    return None
