#!/usr/bin/env python3
# app/api/routes/users.py

from fastapi import APIRouter, Depends, status
from typing import List, Dict, Any
from pydantic import BaseModel

from config.logger import logger
from app.database import crud
from app.database.models import User
from app.api.v1.schemas import UserUpdate, UserResponse
from app.core.utils.auth import get_current_user
from app.core.services.llm.sync import model_sync_service
from app.core.exceptions import AppException, ValidationError

router = APIRouter(prefix="/users", tags=["users"])


# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class PermissionLevelUpdate(BaseModel):
    """Requête pour mettre à jour le permission_level."""
    permission_level: str

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté."""
    return UserResponse(**current_user.to_dict())

@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour les informations de l'utilisateur connecté."""
    success = await crud.update_user(
        user_id=current_user.id,
        name=request.name,
        preferences=request.preferences
    )

    if not success:
        raise AppException("Failed to update user")

    # Récupérer l'utilisateur mis à jour
    user = await crud.get_user(current_user.id)
    user = User.from_row(user)

    return UserResponse(**user.to_dict())

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(current_user: User = Depends(get_current_user)):
    """Supprime le compte de l'utilisateur connecté."""
    success = await crud.delete_user(current_user.id)
    if not success:
        raise AppException("Failed to delete user")

    return None


@router.patch("/me/permission_level", response_model=UserResponse)
async def update_permission_level(
    request: PermissionLevelUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour le niveau de permission pour les tool calls.

    Args:
        request: Nouveau permission_level
        current_user: Utilisateur authentifié

    Returns:
        Utilisateur mis à jour

    Raises:
        400: Invalid permission_level

    Valeurs acceptées:
        - full_auto: Tous les tools s'exécutent sans validation
        - validation_required: Demande validation avant chaque tool call (avec cache)
        - no_tools: Désactive complètement le tool calling
    """
    # Valider le permission_level
    valid_levels = ['full_auto', 'validation_required', 'no_tools']

    if request.permission_level not in valid_levels:
        raise ValidationError(
            f"Invalid permission_level. Must be one of: {', '.join(valid_levels)}"
        )

    # Mettre à jour en base de données
    from app.database.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE users
               SET permission_level = $1, updated_at = NOW()
               WHERE id = $2""",
            request.permission_level, current_user.id
        )

    logger.info(f"User {current_user.id} permission_level updated to {request.permission_level}")

    # Récupérer l'utilisateur mis à jour
    user = await crud.get_user(current_user.id)
    user = User.from_row(user)

    return UserResponse(**user.to_dict())


@router.get("/me/models", response_model=List[Dict[str, Any]])
async def get_my_models(current_user: User = Depends(get_current_user)):
    """
    Récupère les modèles disponibles pour l'utilisateur connecté.
    Si aucun modèle n'est disponible, lance automatiquement la synchronisation depuis les providers.

    Returns:
        Liste des modèles avec leurs informations de service
    """
    try:
        # Récupérer les modèles de l'utilisateur
        models = await crud.list_models_for_user(user_id=current_user.id)

        # Si aucun modèle, synchroniser automatiquement
        if not models or len(models) == 0:
            logger.info(f"No models found for user {current_user.id}, triggering auto-sync...")

            try:
                # Lancer la synchronisation
                sync_report = await model_sync_service.sync_models_to_db()

                logger.info(f"Auto-sync completed: {len(sync_report['created'])} models created, "
                           f"{len(sync_report['already_exists'])} already exist, "
                           f"{len(sync_report['errors'])} errors")

                # Récupérer à nouveau les modèles après sync
                models = await crud.list_models_for_user(user_id=current_user.id)

            except Exception as sync_error:
                logger.error(f"Auto-sync failed: {sync_error}")
                # Ne pas lever d'exception, retourner liste vide
                return []

        return models

    except Exception as e:
        logger.error(f"Error getting models for user {current_user.id}: {e}")
        raise AppException(
            f"Failed to retrieve models: {str(e)}"
        )