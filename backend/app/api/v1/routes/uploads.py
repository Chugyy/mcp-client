from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import quote
from app.database import crud
from app.database.models import User, Upload
from app.api.v1.schemas import UploadResponse
from app.core.utils.auth import get_current_user
from config.config import settings
from config.logger import logger

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Configuration des uploads
UPLOAD_DIR = Path(settings.upload_dir).resolve()
MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024

def encode_filename_header(filename: str, content_disposition: str = "inline") -> str:
    """
    Encode filename for Content-Disposition header to handle unicode characters.

    Uses RFC 2231/5987 encoding:
    - filename: ASCII fallback (sanitized)
    - filename*: UTF-8 encoded version

    Args:
        filename: Original filename (may contain unicode)
        content_disposition: "inline" or "attachment"

    Returns:
        Properly formatted Content-Disposition header value
    """
    # Create ASCII-only fallback by removing accents and non-ASCII chars
    ascii_filename = filename.encode('ascii', 'ignore').decode('ascii')
    if not ascii_filename:
        ascii_filename = "file"

    # RFC 2231/5987 encoded version for unicode support
    encoded_filename = quote(filename, safe='')

    # Return header with both versions for maximum compatibility
    return f'{content_disposition}; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'

# Whitelist des MIME types autorisés
ALLOWED_MIME_TYPES = {
    "avatar": {"image/png", "image/jpeg", "image/jpg", "image/webp"},
    "document": {
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
    "resource": {
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    }
}

@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    upload_type: str = Form("document"),
    agent_id: Optional[str] = Form(None),
    resource_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Upload un fichier (avatar ou document)."""

    # 0. Validation: resource_id OU (agent_id) mais pas les deux
    if resource_id and agent_id:
        raise ValidationError("Cannot specify both resource_id and agent_id"
        )

    # Si resource_id fourni, vérifier qu'elle existe
    if resource_id:
        resource = await crud.get_resource(resource_id)
        if not resource:
            raise NotFoundError("Resource not found")

    # 1. Validation du type
    if upload_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Invalid upload type. Must be one of: {', '.join(ALLOWED_MIME_TYPES.keys())}"
        )

    # 2. Validation du MIME type
    if file.content_type not in ALLOWED_MIME_TYPES[upload_type]:
        raise ValidationError(f"Invalid file type for {upload_type}. Allowed types: {', '.join(ALLOWED_MIME_TYPES[upload_type])}"
        )

    # 3. Validation de la taille (lecture du contenu)
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_SIZE_BYTES:
        raise ValidationError(f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )

    # 4. Vérifier agent_id si fourni
    if agent_id:
        agent = await crud.get_agent(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")

        from app.database.models import Agent
        agent = Agent.from_row(agent)
        if agent.user_id != current_user.id:
            raise PermissionError("Not authorized to upload for this agent")

    # 5. Générer l'upload_id
    from app.core.utils.id_generator import generate_id
    upload_id = generate_id('upload')

    # 6. Extraire l'extension du fichier original
    file_ext = Path(file.filename).suffix.lower()
    if not file_ext:
        # Déterminer l'extension depuis le MIME type si absent
        mime_to_ext = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
            "text/plain": ".txt"
        }
        file_ext = mime_to_ext.get(file.content_type, "")

    # 7. Construire le chemin avec structure scalable
    # Structure: {upload_dir}/{user_id}/{upload_type}/{upload_id}{extension}
    upload_path = UPLOAD_DIR / str(current_user.id) / upload_type
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / f"{upload_id}{file_ext}"

    # 8. Sauvegarder le fichier
    try:
        with file_path.open("wb") as buffer:
            buffer.write(contents)
        logger.info(f"File uploaded: {file_path} ({file_size} bytes)")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise AppException(f"Failed to save file: {str(e)}")

    # 9. Créer l'entrée en base avec l'upload_id pré-généré
    try:
        upload_id = await crud.create_upload(
            user_id=current_user.id if not agent_id and not resource_id else None,
            agent_id=agent_id,
            resource_id=resource_id,
            upload_type=upload_type,
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type,
            upload_id=upload_id
        )

        upload = await crud.get_upload(upload_id)
        upload = Upload.from_row(upload)

        return UploadResponse(**upload.to_dict())

    except Exception as e:
        # Nettoyer le fichier en cas d'erreur DB
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Failed to create upload entry: {e}")
        raise AppException(f"Failed to create upload entry: {str(e)}")

@router.get("/{upload_id}")
async def get_upload_file(upload_id: str, current_user: User = Depends(get_current_user)):
    """
    Serve uploaded file with JWT authentication and ownership verification.

    Args:
        upload_id: ID of the uploaded file
        current_user: Authenticated user from JWT token

    Returns:
        FileResponse: The requested file

    Raises:
        HTTPException 401: No valid JWT token (handled by get_current_user dependency)
        HTTPException 403: User doesn't own the file
        HTTPException 404: File not found
    """
    # Get upload record from database
    upload_dict = await crud.get_upload(upload_id)

    if not upload_dict:
        logger.warning(f"File access denied - file not found: file_id={upload_id}, user_id={current_user.id}")
        raise NotFoundError(
            "File not found"
        )

    upload = Upload.from_row(upload_dict)

    # Verify ownership (or admin override using is_system flag)
    is_owner = False

    # Check direct user ownership
    if upload.user_id and upload.user_id == current_user.id:
        is_owner = True

    # Check agent ownership
    if upload.agent_id:
        agent = await crud.get_agent(upload.agent_id)
        if agent:
            from app.database.models import Agent
            agent = Agent.from_row(agent)
            if agent.user_id == current_user.id:
                is_owner = True

    # Check resource ownership
    if upload.resource_id:
        resource = await crud.get_resource(upload.resource_id)
        if resource:
            # Resources are owned by users, check ownership
            if resource.get('user_id') == current_user.id:
                is_owner = True

    # Admin override - system users can access all files
    if current_user.is_system:
        is_owner = True
        logger.info(f"Admin override: system user {current_user.id} accessing file {upload_id}")

    if not is_owner:
        logger.warning(
            f"File access denied - ownership violation: file_id={upload_id}, "
            f"owner_user_id={upload.user_id}, requester_id={current_user.id}"
        )
        raise PermissionError(
            "You don't have permission to access this file"
        )

    # Resolve file path (handle both absolute and relative paths)
    file_path = Path(upload.file_path)

    # If path is relative, resolve it relative to CWD
    if not file_path.is_absolute():
        file_path = (Path.cwd() / file_path).resolve()
        logger.debug(f"Resolved relative path to absolute: {file_path}")

    if not file_path.exists():
        logger.error(
            f"File access failed - file missing on filesystem: file_id={upload_id}, "
            f"path={file_path}, original_path={upload.file_path}"
        )
        raise NotFoundError(
            "File not found on server"
        )

    # Audit trail logging
    logger.info(
        f"File access granted: file_id={upload_id}, user_id={current_user.id}, "
        f"filename={upload.filename}"
    )

    # Determine content disposition (inline for images/PDFs, attachment for others)
    media_type = upload.mime_type or None  # Auto-detect from extension if None
    content_disposition = "inline"

    if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
        content_disposition = "attachment"

    # Serve file with appropriate headers (unicode-safe filename encoding)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=upload.filename,
        headers={"Content-Disposition": encode_filename_header(upload.filename, content_disposition)}
    )

@router.get("/{upload_id}/download")
async def download(upload_id: str, current_user: User = Depends(get_current_user)):
    """Télécharge un fichier uploadé."""
    upload = await crud.get_upload(upload_id)
    if not upload:
        raise NotFoundError("Upload not found")

    upload = Upload.from_row(upload)

    # Vérifier l'accès
    if upload.user_id and upload.user_id != current_user.id:
        raise PermissionError("Not authorized")

    if upload.agent_id:
        agent = await crud.get_agent(upload.agent_id)
        if agent:
            from app.database.models import Agent
            agent = Agent.from_row(agent)
            if agent.user_id != current_user.id:
                raise PermissionError("Not authorized")

    # Vérifier que le fichier existe
    if not os.path.exists(upload.file_path):
        raise NotFoundError("File not found on disk")

    return FileResponse(
        path=upload.file_path,
        filename=upload.filename,
        media_type=upload.mime_type or "application/octet-stream"
    )

@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(upload_id: str, current_user: User = Depends(get_current_user)):
    """Supprime un upload."""
    upload = await crud.get_upload(upload_id)
    if not upload:
        raise NotFoundError("Upload not found")

    upload = Upload.from_row(upload)

    # Vérifier l'accès
    if upload.user_id and upload.user_id != current_user.id:
        raise PermissionError("Not authorized")

    if upload.agent_id:
        agent = await crud.get_agent(upload.agent_id)
        if agent:
            from app.database.models import Agent
            agent = Agent.from_row(agent)
            if agent.user_id != current_user.id:
                raise PermissionError("Not authorized")

    # Supprimer le fichier du disque
    if os.path.exists(upload.file_path):
        try:
            os.remove(upload.file_path)
        except Exception:
            pass  # Ignorer les erreurs de suppression de fichier

    # Supprimer les embeddings associés à cet upload
    if upload.resource_id:
        from app.database.db import get_pool
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM embeddings WHERE upload_id = $1",
                    upload_id
                )
                logger.info(f"Deleted embeddings for upload {upload_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings for upload {upload_id}: {e}")

    # Supprimer l'entrée en base
    success = await crud.delete_upload(upload_id)
    if not success:
        raise AppException("Failed to delete upload")

    return None
