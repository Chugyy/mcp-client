import asyncpg
import os
import shutil
import uuid
from typing import Optional, Dict, List
from fastapi import UploadFile
from app.database.db import get_pool
from app.core.utils.id_generator import generate_id

# ============================
# UPLOADS
# ============================

async def create_upload(user_id: str = None, agent_id: str = None,
                       upload_type: str = 'document', filename: str = '',
                       file_path: str = '', file_size: int = None,
                       mime_type: str = None, resource_id: str = None, upload_id: str = None) -> str:
    """Crée un upload (fichier)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not upload_id:
            upload_id = generate_id('upload')
        await conn.execute(
            """INSERT INTO uploads (id, user_id, agent_id, resource_id, type, filename,
               file_path, file_size, mime_type)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            upload_id, user_id, agent_id, resource_id, upload_type, filename,
            file_path, file_size, mime_type
        )
        return upload_id

async def get_upload(upload_id: str) -> Optional[Dict]:
    """Récupère un upload par ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM uploads WHERE id = $1", upload_id)
        return dict(result) if result else None

async def list_uploads_by_user(user_id: str, upload_type: str = None) -> List[Dict]:
    """Liste les uploads d'un utilisateur."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if upload_type:
            rows = await conn.fetch(
                "SELECT * FROM uploads WHERE user_id = $1 AND type = $2 ORDER BY created_at DESC",
                user_id, upload_type
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM uploads WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
        return [dict(row) for row in rows]

async def list_uploads_by_agent(agent_id: str, upload_type: str = None) -> List[Dict]:
    """Liste les uploads d'un agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if upload_type:
            rows = await conn.fetch(
                "SELECT * FROM uploads WHERE agent_id = $1 AND type = $2 ORDER BY created_at DESC",
                agent_id, upload_type
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM uploads WHERE agent_id = $1 ORDER BY created_at DESC",
                agent_id
            )
        return [dict(row) for row in rows]

async def list_uploads_by_resource(resource_id: str) -> List[Dict]:
    """Liste tous les uploads d'une resource."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM uploads WHERE resource_id = $1 ORDER BY created_at DESC",
            resource_id
        )
        return [dict(row) for row in rows]

async def delete_upload(upload_id: str) -> bool:
    """Supprime un upload."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM uploads WHERE id = $1", upload_id)
        return int(result.split()[1]) > 0

# ============================
# FILE UPLOAD OPERATIONS
# ============================

async def save_upload(
    agent_id: str,
    file: UploadFile,
    upload_type: str = 'avatar'
) -> str:
    """
    Enregistre un fichier uploadé pour un agent.

    Crée un répertoire unique basé sur le type d'upload, génère un nom de fichier unique,
    sauvegarde le fichier physiquement et insère un enregistrement en base de données.

    Args:
        agent_id: ID de l'agent propriétaire du fichier
        file: Fichier uploadé (UploadFile FastAPI)
        upload_type: Type d'upload (défaut: 'avatar')

    Returns:
        ID de l'upload créé
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Configuration du répertoire d'upload
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

        # Extraire l'extension du fichier
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Construire le chemin complet
        type_dir = os.path.join(upload_dir, upload_type)
        file_path = os.path.join(type_dir, unique_filename)

        # Créer les répertoires nécessaires
        os.makedirs(type_dir, exist_ok=True)

        # Sauvegarder le fichier physiquement
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Récupérer la taille du fichier
        file_size = os.path.getsize(file_path)

        # Insérer en base de données
        upload_id = generate_id('upload')
        await conn.execute(
            """INSERT INTO uploads (id, agent_id, type, filename, file_path, file_size, mime_type)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            upload_id, agent_id, upload_type, file.filename, file_path, file_size, file.content_type
        )

        return upload_id

async def delete_agent_avatar(agent_id: str) -> bool:
    """
    Supprime l'avatar d'un agent.

    Récupère le chemin du fichier avatar, supprime le fichier physiquement (si existe),
    puis supprime l'enregistrement de la base de données.

    Args:
        agent_id: ID de l'agent

    Returns:
        True si l'avatar a été supprimé, False sinon
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer le chemin du fichier avatar
        result = await conn.fetchrow(
            "SELECT file_path FROM uploads WHERE agent_id = $1 AND type = 'avatar'",
            agent_id
        )

        if result:
            file_path = result['file_path']

            # Supprimer le fichier physique (avec gestion d'erreur)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                # Continuer même si la suppression du fichier échoue
                pass

            # Supprimer l'enregistrement en base de données
            delete_result = await conn.execute(
                "DELETE FROM uploads WHERE agent_id = $1 AND type = 'avatar'",
                agent_id
            )

            return int(delete_result.split()[1]) > 0

        return False

async def get_agent_avatar_url(agent_id: str) -> Optional[str]:
    """
    Récupère l'ID de l'upload avatar d'un agent pour construire l'URL authentifiée.

    Récupère l'ID du dernier avatar uploadé pour un agent.
    Le frontend utilisera cet ID avec /api/v1/uploads/{upload_id} (endpoint authentifié).

    Args:
        agent_id: ID de l'agent

    Returns:
        Upload ID de l'avatar ou None si aucun avatar trouvé
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer l'avatar le plus récent
        result = await conn.fetchrow(
            """SELECT id FROM uploads
               WHERE agent_id = $1 AND type = 'avatar'
               ORDER BY created_at DESC LIMIT 1""",
            agent_id
        )

        if result:
            return result['id']

        return None

# ============================
# SERVICE LOGO OPERATIONS
# ============================

async def save_service_logo(
    service_id: str,
    file: UploadFile
) -> str:
    """
    Enregistre le logo d'un service (provider).

    Args:
        service_id: ID du service
        file: Fichier uploadé (UploadFile FastAPI)

    Returns:
        ID de l'upload créé
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Configuration du répertoire d'upload
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

        # Extraire l'extension du fichier
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Construire le chemin complet
        type_dir = os.path.join(upload_dir, 'service_logo')
        file_path = os.path.join(type_dir, unique_filename)

        # Créer les répertoires nécessaires
        os.makedirs(type_dir, exist_ok=True)

        # Sauvegarder le fichier physiquement
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Récupérer la taille du fichier
        file_size = os.path.getsize(file_path)

        # Insérer en base de données
        upload_id = generate_id('upload')
        await conn.execute(
            """INSERT INTO uploads (id, service_id, type, filename, file_path, file_size, mime_type)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            upload_id, service_id, 'service_logo', file.filename, file_path, file_size, file.content_type
        )

        return upload_id

async def delete_service_logo(service_id: str) -> bool:
    """
    Supprime le logo d'un service.

    Args:
        service_id: ID du service

    Returns:
        True si le logo a été supprimé, False sinon
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer le chemin du fichier logo
        result = await conn.fetchrow(
            "SELECT file_path FROM uploads WHERE service_id = $1 AND type = 'service_logo'",
            service_id
        )

        if result:
            file_path = result['file_path']

            # Supprimer le fichier physique (avec gestion d'erreur)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

            # Supprimer l'enregistrement en base de données
            delete_result = await conn.execute(
                "DELETE FROM uploads WHERE service_id = $1 AND type = 'service_logo'",
                service_id
            )

            return int(delete_result.split()[1]) > 0

        return False

async def get_service_logo_url(service_id: str) -> Optional[str]:
    """
    Récupère l'URL d'accès au logo d'un service.

    Args:
        service_id: ID du service

    Returns:
        URL relative du fichier logo ou None si aucun logo trouvé
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Récupérer le logo le plus récent
        result = await conn.fetchrow(
            """SELECT file_path FROM uploads
               WHERE service_id = $1 AND type = 'service_logo'
               ORDER BY created_at DESC LIMIT 1""",
            service_id
        )

        if result:
            file_path = result['file_path']
            filename = os.path.basename(file_path)
            return f"/uploads/service_logo/{filename}"

        return None
