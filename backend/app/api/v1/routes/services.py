from fastapi import APIRouter, Depends, status, Query, File, UploadFile
from typing import List, Optional
from app.database import crud
from app.database.models import User
from app.api.v1.schemas import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse
)
from app.core.utils.auth import get_current_user
from app.database.crud import uploads
from app.core.exceptions import ValidationError, NotFoundError, AppException

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/providers", response_model=List[str])
async def list_available_providers(
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les types de providers disponibles dans le système.

    Retourne les valeurs uniques de la colonne 'provider' en base.
    Utile pour construire des filtres dynamiques côté frontend.

    **Exemple de retour :** `["anthropic", "mcp", "openai", "resource"]`
    """
    from app.database.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT provider FROM services ORDER BY provider"
        )
        return [row['provider'] for row in rows]

@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    request: ServiceCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crée un nouveau service externe (LLM, MCP, Resource).
    """
    try:
        service_id = await crud.create_service(
            name=request.name,
            provider=request.provider,
            description=request.description,
            status=request.status
        )
    except Exception as e:
        raise ValidationError(str(e))

    service = await crud.get_service(service_id)
    if not service:
        raise AppException("Failed to create service")

    return ServiceResponse(**service)

@router.get("", response_model=List[ServiceResponse])
async def list_services(
    provider: Optional[str] = Query(
        None,
        description="Filtrer par provider(s). Exemples: 'openai' ou 'openai,anthropic' (séparés par virgule)"
    ),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrer par status (active, inactive, deprecated)"),
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les services avec filtres optionnels.

    **Exemples d'usage :**
    - `/services` - Tous les services
    - `/services?provider=openai` - Seulement OpenAI
    - `/services?provider=openai,anthropic` - OpenAI + Anthropic
    - `/services?provider=openai,anthropic&status=active` - OpenAI + Anthropic actifs
    """
    # Parser les providers multiples (format CSV)
    providers_list = None
    if provider:
        providers_list = [p.strip() for p in provider.split(',')]

    services = await crud.list_services(provider=providers_list, status=status_filter)
    return [ServiceResponse(**s) for s in services]

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère un service par ID.
    """
    service = await crud.get_service(service_id)
    if not service:
        raise NotFoundError("Service not found")

    return ServiceResponse(**service)

@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    request: ServiceUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour un service.
    """
    service = await crud.get_service(service_id)
    if not service:
        raise NotFoundError("Service not found")

    try:
        success = await crud.update_service(
            service_id=service_id,
            name=request.name,
            provider=request.provider,
            description=request.description,
            status=request.status
        )
    except Exception as e:
        raise ValidationError(str(e))

    if not success:
        raise AppException("Failed to update service")

    updated_service = await crud.get_service(service_id)
    return ServiceResponse(**updated_service)

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un service.
    Note: Cela supprimera en cascade tous les models associés.
    """
    service = await crud.get_service(service_id)
    if not service:
        raise NotFoundError("Service not found")

    success = await crud.delete_service(service_id)
    if not success:
        raise AppException("Failed to delete service")

    return None


@router.patch("/{service_id}/logo")
async def upload_service_logo(
    service_id: str,
    logo: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload ou met à jour le logo d'un service provider (OpenAI, Anthropic, etc.).

    Le fichier sera stocké dans /uploads/service_logo/ et lié au service via logo_upload_id.
    """
    # Vérifier que le service existe
    service = await crud.get_service(service_id)
    if not service:
        raise NotFoundError("Service not found")

    # Supprimer l'ancien logo s'il existe
    await uploads.delete_service_logo(service_id)

    # Upload du nouveau logo
    upload_id = await uploads.save_service_logo(service_id, logo)

    # Mettre à jour le service avec le logo_upload_id
    await crud.update_service(service_id, logo_upload_id=upload_id)

    return {
        "service_id": service_id,
        "logo_upload_id": upload_id,
        "message": "Logo uploaded successfully"
    }
