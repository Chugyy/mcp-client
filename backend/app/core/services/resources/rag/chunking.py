"""Chunking de documents."""

from typing import List
from config.config import settings
from app.database import crud

def chunk_text(text: str) -> List[str]:
    """Simple chunking par caractères avec overlap."""
    chunks = []
    start = 0
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
        if start >= len(text):
            break

    return chunks

async def chunk_document(upload_id: str) -> List[str]:
    """Charge et chunke un document depuis uploads."""
    upload = await crud.get_upload(upload_id)
    if not upload:
        raise ValueError(f"Upload {upload_id} not found")

    file_path = upload['file_path']
    mime_type = upload.get('mime_type', '')

    # Support basique : TXT, PDF
    if 'text/plain' in mime_type:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

    elif 'pdf' in mime_type:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])

    else:
        raise ValueError(f"Unsupported mime_type: {mime_type}")

    return chunk_text(text)
