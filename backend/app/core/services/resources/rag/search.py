"""Recherche vectorielle dans les ressources."""

from typing import List, Dict, Any
from app.database.db import get_connection
from app.database import crud
from .embeddings import embed_texts

async def search(query: str, resource_ids: List[str], top_k: int = 5) -> Dict[str, Any]:
    """
    Recherche vectorielle dans les ressources.

    Args:
        query: Requête de recherche
        resource_ids: Liste des IDs de ressources à interroger
        top_k: Nombre de résultats

    Returns:
        {
            "contexts": List[str],  # Chunks pertinents
            "sources": List[str],   # Resource IDs sources (pour compatibilité)
            "upload_ids": List[str],  # Upload IDs
            "detailed_sources": List[Dict],  # Sources détaillées avec métadonnées
            "count": int
        }
    """
    # Générer embedding de la query
    query_vector = (await embed_texts([query]))[0]

    # Convertir le vecteur en string pour pgvector
    query_vector_str = str(query_vector)

    # Search dans pgvector
    conn = await get_connection()

    # Filtrer par resource_ids si fournis
    if resource_ids:
        placeholders = ','.join([f"${i+2}" for i in range(len(resource_ids))])
        query_sql = f"""
            SELECT e.id, e.text, e.resource_id, e.upload_id, e.chunk_index,
                   e.vector <=> $1::halfvec AS distance,
                   r.name as resource_name
            FROM embeddings e
            JOIN resources r ON e.resource_id = r.id
            WHERE e.resource_id IN ({placeholders})
            ORDER BY distance
            LIMIT {top_k}
        """
        rows = await conn.fetch(query_sql, query_vector_str, *resource_ids)
    else:
        rows = await conn.fetch(
            """SELECT e.id, e.text, e.resource_id, e.upload_id, e.chunk_index,
                      e.vector <=> $1::halfvec AS distance,
                      r.name as resource_name
               FROM embeddings e
               JOIN resources r ON e.resource_id = r.id
               ORDER BY distance
               LIMIT $2""",
            query_vector_str, top_k
        )

    await conn.close()

    # Formater résultats
    contexts = [row['text'] for row in rows]
    sources = list(set([row['resource_id'] for row in rows]))
    upload_ids = list(set([row['upload_id'] for row in rows]))

    # Créer la liste détaillée des sources pour le frontend
    detailed_sources = [
        {
            "resource_id": row['resource_id'],
            "resource_name": row['resource_name'],
            "chunk_id": row['id'],
            "similarity": float(1 - row['distance']),  # Convertir distance cosinus en similarité
            "content": row['text'][:200] + "..." if len(row['text']) > 200 else row['text']  # Extrait
        }
        for row in rows
    ]

    return {
        "contexts": contexts,
        "sources": sources,
        "upload_ids": upload_ids,
        "detailed_sources": detailed_sources,
        "count": len(contexts)
    }

async def list_resources(resource_ids: List[str]) -> List[Dict[str, Any]]:
    """Liste les ressources disponibles."""

    if resource_ids:
        # Lister les ressources spécifiées
        resources = []
        for rid in resource_ids:
            res = await crud.get_resource(rid)
            if res and res['status'] == 'ready':
                resources.append({
                    "id": res['id'],
                    "name": res['name'],
                    "description": res.get('description'),
                    "chunk_count": res.get('chunk_count', 0)
                })
        return resources
    else:
        # Fallback: Lister toutes les ressources 'ready' (même comportement que search)
        from app.database.db import get_connection
        conn = await get_connection()

        rows = await conn.fetch(
            """SELECT DISTINCT r.id, r.name, r.description,
                      COUNT(e.id) as chunk_count
               FROM resources r
               LEFT JOIN embeddings e ON r.id = e.resource_id
               WHERE r.status = 'ready'
               GROUP BY r.id, r.name, r.description
               ORDER BY r.name"""
        )
        await conn.close()

        return [
            {
                "id": row['id'],
                "name": row['name'],
                "description": row['description'],
                "chunk_count": row['chunk_count'] or 0
            }
            for row in rows
        ]
