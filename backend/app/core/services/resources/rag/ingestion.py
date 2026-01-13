"""Pipeline d'ingestion de ressources."""

from config.logger import logger
from app.database import crud
from app.database.db import get_connection
from .chunking import chunk_document
from .embeddings import embed_texts

async def ingest_resource(resource_id: str):
    """
    Ingère une ressource : chunks + embeddings → DB.

    Steps:
        0. Nettoyer les anciens embeddings (réindexation complète)
        1. Récupérer les uploads liés à cette ressource
        2. Chunker chaque document
        3. Générer embeddings
        4. Stocker dans table embeddings
        5. Mettre à jour status resource
    """
    # Marquer comme processing
    await crud.update_resource_status(resource_id, 'processing')

    try:
        # Nettoyer les anciens embeddings pour réindexation complète
        conn = await get_connection()
        await conn.execute(
            "DELETE FROM embeddings WHERE resource_id = $1",
            resource_id
        )
        await conn.close()
        logger.info(f"Cleaned old embeddings for resource {resource_id}")

        # Récupérer les uploads liés
        conn = await get_connection()
        upload_rows = await conn.fetch(
            "SELECT * FROM uploads WHERE resource_id = $1",
            resource_id
        )
        await conn.close()

        if not upload_rows:
            raise ValueError(f"No uploads found for resource {resource_id}")

        total_chunks = 0

        for upload_row in upload_rows:
            upload_id = upload_row['id']

            logger.info(f"Processing upload {upload_id} for resource {resource_id}")

            # Chunker
            chunks = await chunk_document(upload_id)

            # Embeddings (batch) - async call
            vectors = await embed_texts(chunks)

            # Insérer dans embeddings table
            conn = await get_connection()
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                # Convertir le vecteur en format pgvector (string)
                vector_str = str(vector)
                await conn.execute(
                    """INSERT INTO embeddings (resource_id, upload_id, chunk_index, text, vector)
                       VALUES ($1, $2, $3, $4, $5::halfvec)""",
                    resource_id, upload_id, i, chunk, vector_str
                )
            await conn.close()

            total_chunks += len(chunks)
            logger.info(f"Indexed {len(chunks)} chunks from upload {upload_id}")

        # Marquer comme ready
        await crud.update_resource_status(
            resource_id,
            'ready',
            chunk_count=total_chunks
        )

        logger.info(f"Resource {resource_id} ingestion complete: {total_chunks} chunks")

    except Exception as e:
        logger.error(f"Ingestion error for resource {resource_id}: {e}")

        # Marquer comme error
        await crud.update_resource_status(
            resource_id,
            'error',
            error_message=str(e)
        )

        raise
