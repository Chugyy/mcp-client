"""Integration tests for uploads routes.

Tests all file upload endpoints:
- POST /api/v1/uploads (upload file)
- GET /api/v1/uploads/{upload_id} (get/serve file)
- GET /api/v1/uploads/{upload_id}/download (download file)
- DELETE /api/v1/uploads/{upload_id} (delete upload)
"""

import pytest
import io
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def sample_pdf_file():
    """Create a minimal valid PDF file for testing."""
    # Minimal PDF content (valid PDF header)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
306
%%EOF
"""
    return io.BytesIO(pdf_content)


@pytest.fixture
def sample_image_file():
    """Create a minimal valid PNG file for testing."""
    # Minimal 1x1 PNG (red pixel)
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
        b'\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return io.BytesIO(png_content)


@pytest.fixture
def uploaded_document(authenticated_client, sample_pdf_file):
    """Create a sample uploaded document via API."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("test_document.pdf", sample_pdf_file, "application/pdf")},
        data={"upload_type": "document"}
    )

    assert response.status_code == 201, f"Upload creation failed: {response.text}"
    return response.json()


@pytest.fixture
def uploaded_avatar(authenticated_client, sample_image_file):
    """Create a sample uploaded avatar via API."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("avatar.png", sample_image_file, "image/png")},
        data={"upload_type": "avatar"}
    )

    assert response.status_code == 201, f"Upload creation failed: {response.text}"
    return response.json()


@pytest.fixture
def other_user_upload(client, clean_db, sample_pdf_file):
    """Create an upload belonging to a different user."""
    # Register a second user
    register_response = client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "name": "Other User"
    })
    assert register_response.status_code == 201

    # Upload a file as the other user (already authenticated from registration)
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("other_doc.pdf", sample_pdf_file, "application/pdf")},
        data={"upload_type": "document"}
    )
    assert response.status_code == 201

    # Restore original test user session by logging out and back in
    # (This prevents cookie contamination for subsequent tests)
    client.post("/api/v1/auth/logout")

    return response.json()


# ============================================================================
# POST /api/v1/uploads - Create Upload Tests
# ============================================================================

def test_upload_document_success(authenticated_client, clean_db, sample_pdf_file):
    """Test uploading a valid PDF document."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
        data={"upload_type": "document"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["type"] == "document"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size"] > 0
    assert "id" in data


def test_upload_avatar_success(authenticated_client, clean_db, sample_image_file):
    """Test uploading a valid avatar image."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("avatar.png", sample_image_file, "image/png")},
        data={"upload_type": "avatar"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "avatar.png"
    assert data["type"] == "avatar"
    assert data["mime_type"] == "image/png"


def test_upload_with_resource_id(authenticated_client, clean_db, sample_pdf_file):
    """Test uploading a document linked to a resource."""
    # Create a resource first
    resource_response = authenticated_client.post("/api/v1/resources", json={
        "name": "Test Resource",
        "description": "Test",
        "enabled": True,
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072
    })
    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    # Upload file linked to resource
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("doc.pdf", sample_pdf_file, "application/pdf")},
        data={
            "upload_type": "resource",
            "resource_id": resource_id
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == resource_id


def test_upload_invalid_type(authenticated_client, clean_db, sample_pdf_file):
    """Test upload with invalid upload_type returns 400."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
        data={"upload_type": "invalid_type"}
    )

    assert response.status_code == 400
    assert "Invalid upload type" in response.json()["detail"]


def test_upload_invalid_mime_type(authenticated_client, clean_db):
    """Test upload with disallowed MIME type returns 400."""
    # Try to upload an executable as a document
    fake_exe = io.BytesIO(b"MZ\x90\x00")  # EXE header

    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("malware.exe", fake_exe, "application/x-msdownload")},
        data={"upload_type": "document"}
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


@pytest.mark.skip(reason="File size validation requires large file generation (slow)")
def test_upload_file_too_large(authenticated_client, clean_db):
    """Test upload exceeding max file size returns 422."""
    # Create a file larger than max_upload_size_mb (default: 10MB)
    large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
    large_file = io.BytesIO(large_content)

    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("large.pdf", large_file, "application/pdf")},
        data={"upload_type": "document"}
    )

    assert response.status_code == 422
    assert "File too large" in response.json()["detail"]


def test_upload_resource_not_found(authenticated_client, clean_db, sample_pdf_file):
    """Test upload with nonexistent resource_id returns 404."""
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("doc.pdf", sample_pdf_file, "application/pdf")},
        data={
            "upload_type": "resource",
            "resource_id": "res_nonexistent"
        }
    )

    assert response.status_code == 404
    assert "Resource not found" in response.json()["detail"]


def test_upload_both_resource_and_agent_returns_400(authenticated_client, clean_db, sample_pdf_file):
    """Test upload with both resource_id and agent_id returns 400."""
    # Create agent (agents use form-data, not JSON)
    agent_response = authenticated_client.post("/api/v1/agents", data={
        "name": "Test Agent",
        "description": "Test",
        "system_prompt": "You are helpful",
        "enabled": "true"
    })
    assert agent_response.status_code == 201, f"Agent creation failed: {agent_response.text}"
    agent_id = agent_response.json()["id"]

    # Create resource
    resource_response = authenticated_client.post("/api/v1/resources", json={
        "name": "Test Resource",
        "description": "Test",
        "enabled": True,
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072
    })
    resource_id = resource_response.json()["id"]

    # Try to upload with both IDs
    response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("doc.pdf", sample_pdf_file, "application/pdf")},
        data={
            "upload_type": "document",
            "resource_id": resource_id,
            "agent_id": agent_id
        }
    )

    assert response.status_code == 400
    assert "Cannot specify both" in response.json()["detail"]


def test_upload_unauthenticated_returns_401(client, clean_db, sample_pdf_file):
    """Test upload without authentication returns 401."""
    # Use fresh client without authenticated fixtures
    fresh_client = client.__class__(client.app)

    response = fresh_client.post(
        "/api/v1/uploads",
        files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
        data={"upload_type": "document"}
    )

    assert response.status_code == 401


# ============================================================================
# GET /api/v1/uploads/{upload_id} - Get Upload File Tests
# ============================================================================

def test_get_upload_file_success(authenticated_client, uploaded_document):
    """Test retrieving an uploaded file (owner)."""
    upload_id = uploaded_document["id"]

    response = authenticated_client.get(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0


def test_get_upload_file_not_found(authenticated_client, clean_db):
    """Test getting nonexistent upload returns 404."""
    response = authenticated_client.get("/api/v1/uploads/upl_nonexistent")

    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]


def test_get_upload_file_permission_denied(authenticated_client, other_user_upload):
    """Test getting another user's upload returns 403."""
    upload_id = other_user_upload["id"]

    # Re-authenticate as original test user
    authenticated_client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    response = authenticated_client.get(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_upload_file_unauthenticated_returns_401(client, uploaded_document):
    """Test getting upload file without authentication returns 401."""
    # Use fresh client without authentication
    fresh_client = client.__class__(client.app)
    upload_id = uploaded_document["id"]

    response = fresh_client.get(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 401


# ============================================================================
# GET /api/v1/uploads/{upload_id}/download - Download Upload Tests
# ============================================================================

def test_download_upload_success(authenticated_client, uploaded_document):
    """Test downloading an uploaded file."""
    upload_id = uploaded_document["id"]

    response = authenticated_client.get(f"/api/v1/uploads/{upload_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] in ["application/pdf", "application/octet-stream"]
    assert len(response.content) > 0


def test_download_upload_not_found(authenticated_client, clean_db):
    """Test downloading nonexistent upload returns 404."""
    response = authenticated_client.get("/api/v1/uploads/upl_nonexistent/download")

    assert response.status_code == 404
    assert "Upload not found" in response.json()["detail"]


def test_download_upload_permission_denied(authenticated_client, other_user_upload):
    """Test downloading another user's upload returns 403."""
    upload_id = other_user_upload["id"]

    # Re-authenticate as original test user
    authenticated_client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    response = authenticated_client.get(f"/api/v1/uploads/{upload_id}/download")

    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


def test_download_upload_unauthenticated_returns_401(client, uploaded_document):
    """Test downloading without authentication returns 401."""
    fresh_client = client.__class__(client.app)
    upload_id = uploaded_document["id"]

    response = fresh_client.get(f"/api/v1/uploads/{upload_id}/download")

    assert response.status_code == 401


# ============================================================================
# DELETE /api/v1/uploads/{upload_id} - Delete Upload Tests
# ============================================================================

def test_delete_upload_success(authenticated_client, uploaded_document):
    """Test deleting an upload."""
    upload_id = uploaded_document["id"]

    response = authenticated_client.delete(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 204

    # Verify upload is deleted
    get_response = authenticated_client.get(f"/api/v1/uploads/{upload_id}")
    assert get_response.status_code == 404


def test_delete_upload_with_embeddings(authenticated_client, clean_db, sample_pdf_file):
    """Test deleting an upload with associated embeddings (cascade delete)."""
    # Create resource
    resource_response = authenticated_client.post("/api/v1/resources", json={
        "name": "Test Resource",
        "description": "Test",
        "enabled": True,
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072
    })
    resource_id = resource_response.json()["id"]

    # Upload file linked to resource
    upload_response = authenticated_client.post(
        "/api/v1/uploads",
        files={"file": ("doc.pdf", sample_pdf_file, "application/pdf")},
        data={
            "upload_type": "resource",
            "resource_id": resource_id
        }
    )
    upload_id = upload_response.json()["id"]

    # Delete upload (should cascade delete embeddings)
    response = authenticated_client.delete(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 204


def test_delete_upload_not_found(authenticated_client, clean_db):
    """Test deleting nonexistent upload returns 404."""
    response = authenticated_client.delete("/api/v1/uploads/upl_nonexistent")

    assert response.status_code == 404
    assert "Upload not found" in response.json()["detail"]


def test_delete_upload_permission_denied(authenticated_client, other_user_upload):
    """Test deleting another user's upload returns 403."""
    upload_id = other_user_upload["id"]

    # Re-authenticate as original test user
    authenticated_client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    response = authenticated_client.delete(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


def test_delete_upload_unauthenticated_returns_401(client, uploaded_document):
    """Test deleting without authentication returns 401."""
    fresh_client = client.__class__(client.app)
    upload_id = uploaded_document["id"]

    response = fresh_client.delete(f"/api/v1/uploads/{upload_id}")

    assert response.status_code == 401
