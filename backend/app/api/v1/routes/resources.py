#!/usr/bin/env python3
# app/api/v1/routes/resources.py
"""
Routes API pour les ressources RAG.
Refactorisé selon le pattern MCP.
"""

from fastapi import APIRouter, Header, Depends
from typing import Optional, List
from app.core.utils.auth import get_current_user
from app.core.exceptions import ConflictError
from app.database.models import User, Resource
from app.api.v1.schemas.resources import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceWithUploadsResponse
)
from app.core.services.resources.manager import ResourceManager
from app.database.crud import resources as crud

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_resource(
    request: ResourceCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crée une nouvelle ressource RAG.

    Validations:
    - Nom unique par utilisateur
    - Quota non dépassé
    - Configuration embeddings valide
    """
    resource_id = await ResourceManager.create(request, current_user.id)
    resource_data = await crud.get_resource(resource_id)
    return ResourceResponse(**Resource.from_row(resource_data).to_dict())


@router.get("", response_model=List[ResourceResponse])
async def list_resources(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Liste les ressources de l'utilisateur connecté.

    ⚠️ SÉCURITÉ: Filtre automatiquement par user_id.
    """
    resources = await crud.list_resources_by_user(
        user_id=current_user.id,
        enabled_only=enabled_only
    )
    return [
        ResourceResponse(**Resource.from_row(r).to_dict())
        for r in resources
    ]


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère une ressource par ID.

    Vérifie automatiquement l'ownership.
    """
    resource_data = await ResourceManager.get(resource_id, current_user.id)
    return ResourceResponse(**Resource.from_row(resource_data).to_dict())


@router.patch("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    request: ResourceUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour une ressource.

    Vérifie ownership et unicité du nom.
    """
    await ResourceManager.update(resource_id, request, current_user.id)
    updated = await crud.get_resource(resource_id)
    return ResourceResponse(**Resource.from_row(updated).to_dict())


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    x_confirm_deletion: Optional[str] = Header(None)
):
    """
    Supprime une ressource.

    Si impact détecté (agents liés), retourne 409 Conflict.
    Pour forcer la suppression, passer X-Confirm-Deletion: true.
    """
    force = x_confirm_deletion == "true"

    try:
        await ResourceManager.delete(resource_id, current_user.id, force=force)
    except RuntimeError as e:
        # Impact détecté sans confirmation
        impact = await crud.get_resource_deletion_impact(resource_id)
        raise ConflictError(
            str(e),
            details={
                "type": "confirmation_required",
                "impact": impact
            }
        )

    return None


@router.get("/{resource_id}/uploads", response_model=List[dict])
async def list_resource_uploads(
    resource_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Liste les uploads d'une ressource.

    Vérifie ownership de la ressource.
    """
    from app.database.crud import uploads as crud_uploads

    # Vérifier ownership
    await ResourceManager.get(resource_id, current_user.id)

    # Lister uploads
    uploads = await crud_uploads.list_uploads_by_resource(resource_id)
    return uploads


@router.post("/{resource_id}/ingest")
async def ingest_resource_endpoint(
    resource_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Déclenche l'ingestion RAG d'une ressource.

    Vérifie ownership avant de lancer le pipeline.
    """
    from app.core.services.resources.rag.ingestion import ingest_resource

    # Vérifier ownership
    await ResourceManager.get(resource_id, current_user.id)

    # Lancer ingestion en arrière-plan
    await ingest_resource(resource_id)

    return {
        "success": True,
        "message": "Resource ingestion started"
    }
