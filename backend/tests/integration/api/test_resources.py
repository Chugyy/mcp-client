"""Integration tests for resources routes.

Tests all RAG Resource endpoints:
- POST /api/v1/resources (create resource)
- GET /api/v1/resources (list resources)
- GET /api/v1/resources/{resource_id} (get by ID)
- PATCH /api/v1/resources/{resource_id} (update)
- DELETE /api/v1/resources/{resource_id} (delete with impact check)
- GET /api/v1/resources/{resource_id}/uploads (list uploads)
- POST /api/v1/resources/{resource_id}/ingest (trigger ingestion)
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture
def created_resource(authenticated_client, clean_db):
    """Create a sample resource via API.

    Resources are RAG storage entities with embedding configuration.
    """
    response = authenticated_client.post("/api/v1/resources", json={
        "name": "Test Resource",
        "description": "Test resource for integration tests",
        "enabled": True,
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072
    })

    assert response.status_code == 201, f"Resource creation failed: {response.text}"
    return response.json()


@pytest.fixture
def other_user_resource(client, clean_db, test_user):
    """Create a resource belonging to a different user.

    Useful for testing authorization and permission checks.
    """
    # Register a second user
    register_response = client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "name": "Other User"
    })
    assert register_response.status_code == 201

    # Login as the other user
    login_response = client.post("/api/v1/auth/login", json={
        "email": "other@example.com",
        "password": "otherpass123"
    })
    assert login_response.status_code == 200

    # Create a resource as the other user
    resource_response = client.post("/api/v1/resources", json={
        "name": "Other User Resource",
        "description": "Resource belonging to another user",
        "enabled": True,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536
    })
    assert resource_response.status_code == 201

    resource_data = resource_response.json()

    # Restore original user's session
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    return resource_data


# =============================================================================
# POST /resources - Create resource
# =============================================================================

def test_create_resource_success(authenticated_client, clean_db):
    """Test creating a resource with valid data."""
    response = authenticated_client.post("/api/v1/resources", json={
        "name": "My Resource",
        "description": "A test resource",
        "enabled": True,
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Resource"
    assert data["description"] == "A test resource"
    assert data["enabled"] is True
    assert data["embedding_model"] == "text-embedding-3-large"
    assert data["embedding_dim"] == 3072
    assert data["status"] == "pending"  # New resources start in pending status
    assert "id" in data


def test_create_resource_minimal_fields(authenticated_client, clean_db):
    """Test creating a resource with minimal required fields (defaults)."""
    response = authenticated_client.post("/api/v1/resources", json={
        "name": "Minimal Resource",
        "enabled": True
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Resource"
    assert data["embedding_model"] == "text-embedding-3-large"  # Default
    assert data["embedding_dim"] == 3072  # Default


def test_create_resource_invalid_embedding_model(authenticated_client, clean_db):
    """Test creating a resource with invalid embedding model returns 422."""
    response = authenticated_client.post("/api/v1/resources", json={
        "name": "Invalid Model Resource",
        "enabled": True,
        "embedding_model": "invalid-model",
        "embedding_dim": 1536
    })

    assert response.status_code == 422
    error = response.json()
    assert "detail" in error


def test_create_resource_mismatched_dimensions(authenticated_client, clean_db):
    """Test creating a resource with mismatched model/dimension returns 422."""
    response = authenticated_client.post("/api/v1/resources", json={
        "name": "Mismatched Resource",
        "enabled": True,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 3072  # Wrong! Should be 1536
    })

    assert response.status_code == 422
    error = response.json()
    assert "detail" in error


def test_create_resource_duplicate_name(authenticated_client, clean_db):
    """Test creating a resource with duplicate name returns 409."""
    # Create first resource
    response1 = authenticated_client.post("/api/v1/resources", json={
        "name": "Unique Name",
        "enabled": True
    })
    assert response1.status_code == 201

    # Try to create another with same name
    response2 = authenticated_client.post("/api/v1/resources", json={
        "name": "Unique Name",
        "enabled": True
    })

    assert response2.status_code == 409
    error = response2.json()
    assert "detail" in error


def test_create_resource_unauthenticated(client, clean_db):
    """Test creating a resource without authentication returns 401."""
    response = client.post("/api/v1/resources", json={
        "name": "Unauthenticated Resource",
        "enabled": True
    })

    assert response.status_code == 401


# =============================================================================
# GET /resources - List resources
# =============================================================================

def test_list_resources_empty(authenticated_client, clean_db):
    """Test listing resources when none exist."""
    response = authenticated_client.get("/api/v1/resources")

    assert response.status_code == 200
    assert response.json() == []


def test_list_resources_with_resources(authenticated_client, clean_db):
    """Test listing resources with multiple resources."""
    # Create multiple resources
    authenticated_client.post("/api/v1/resources", json={
        "name": "Resource 1",
        "enabled": True
    })
    authenticated_client.post("/api/v1/resources", json={
        "name": "Resource 2",
        "enabled": False
    })

    response = authenticated_client.get("/api/v1/resources")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_resources_enabled_only_filter(authenticated_client, clean_db):
    """Test listing resources with enabled_only filter."""
    # Create enabled and disabled resources
    authenticated_client.post("/api/v1/resources", json={
        "name": "Enabled Resource",
        "enabled": True
    })
    authenticated_client.post("/api/v1/resources", json={
        "name": "Disabled Resource",
        "enabled": False
    })

    response = authenticated_client.get("/api/v1/resources?enabled_only=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Enabled Resource"
    assert data[0]["enabled"] is True


def test_list_resources_filters_by_user(authenticated_client, other_user_resource, clean_db):
    """Test that list resources only shows current user's resources."""
    # Create a resource for current user
    authenticated_client.post("/api/v1/resources", json={
        "name": "My Resource",
        "enabled": True
    })

    response = authenticated_client.get("/api/v1/resources")

    assert response.status_code == 200
    data = response.json()
    # Should only see current user's resource, not other_user_resource
    assert len(data) == 1
    assert data[0]["name"] == "My Resource"


def test_list_resources_unauthenticated(client, clean_db):
    """Test listing resources without authentication returns 401."""
    response = client.get("/api/v1/resources")

    assert response.status_code == 401


# =============================================================================
# GET /resources/{resource_id} - Get resource by ID
# =============================================================================

def test_get_resource_success(authenticated_client, created_resource):
    """Test getting a resource by ID."""
    resource_id = created_resource["id"]

    response = authenticated_client.get(f"/api/v1/resources/{resource_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == resource_id
    assert data["name"] == created_resource["name"]


def test_get_resource_not_found(authenticated_client, clean_db):
    """Test getting a non-existent resource returns 404."""
    response = authenticated_client.get("/api/v1/resources/rsc_nonexistent")

    assert response.status_code == 404
    error = response.json()
    assert "detail" in error


def test_get_resource_permission_denied(authenticated_client, other_user_resource):
    """Test getting another user's resource returns 403."""
    response = authenticated_client.get(f"/api/v1/resources/{other_user_resource['id']}")

    assert response.status_code == 403
    error = response.json()
    assert "detail" in error


def test_get_resource_unauthenticated(client, clean_db):
    """Test getting a resource without authentication returns 401."""
    response = client.get("/api/v1/resources/rsc_any_id")

    assert response.status_code == 401


# =============================================================================
# PATCH /resources/{resource_id} - Update resource
# =============================================================================

def test_update_resource_success(authenticated_client, created_resource):
    """Test updating a resource with valid data."""
    resource_id = created_resource["id"]

    response = authenticated_client.patch(f"/api/v1/resources/{resource_id}", json={
        "name": "Updated Resource",
        "description": "Updated description",
        "enabled": False
    })

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Resource"
    assert data["description"] == "Updated description"
    assert data["enabled"] is False


def test_update_resource_partial(authenticated_client, created_resource):
    """Test partial update (only some fields)."""
    resource_id = created_resource["id"]

    response = authenticated_client.patch(f"/api/v1/resources/{resource_id}", json={
        "description": "Only description updated"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == created_resource["name"]  # Unchanged
    assert data["description"] == "Only description updated"


def test_update_resource_duplicate_name(authenticated_client, clean_db):
    """Test updating to duplicate name returns 409."""
    # Create two resources
    resource1 = authenticated_client.post("/api/v1/resources", json={
        "name": "Resource 1",
        "enabled": True
    }).json()

    resource2 = authenticated_client.post("/api/v1/resources", json={
        "name": "Resource 2",
        "enabled": True
    }).json()

    # Try to update resource2 to have resource1's name
    response = authenticated_client.patch(f"/api/v1/resources/{resource2['id']}", json={
        "name": "Resource 1"
    })

    assert response.status_code == 409
    error = response.json()
    assert "detail" in error


def test_update_resource_not_found(authenticated_client, clean_db):
    """Test updating a non-existent resource returns 404."""
    response = authenticated_client.patch("/api/v1/resources/rsc_nonexistent", json={
        "name": "Updated"
    })

    assert response.status_code == 404


def test_update_resource_permission_denied(authenticated_client, other_user_resource):
    """Test updating another user's resource returns 403."""
    response = authenticated_client.patch(
        f"/api/v1/resources/{other_user_resource['id']}",
        json={"name": "Hacked"}
    )

    assert response.status_code == 403


def test_update_resource_unauthenticated(client, clean_db):
    """Test updating a resource without authentication returns 401."""
    response = client.patch("/api/v1/resources/rsc_any_id", json={
        "name": "Updated"
    })

    assert response.status_code == 401


# =============================================================================
# DELETE /resources/{resource_id} - Delete resource
# =============================================================================

def test_delete_resource_success(authenticated_client, created_resource):
    """Test deleting a resource without dependencies."""
    resource_id = created_resource["id"]

    response = authenticated_client.delete(f"/api/v1/resources/{resource_id}")

    assert response.status_code == 204

    # Verify deletion
    get_response = authenticated_client.get(f"/api/v1/resources/{resource_id}")
    assert get_response.status_code == 404


def test_delete_resource_with_confirmation(authenticated_client, created_resource):
    """Test deleting a resource with X-Confirm-Deletion header."""
    resource_id = created_resource["id"]

    response = authenticated_client.delete(
        f"/api/v1/resources/{resource_id}",
        headers={"X-Confirm-Deletion": "true"}
    )

    assert response.status_code == 204


def test_delete_resource_not_found(authenticated_client, clean_db):
    """Test deleting a non-existent resource returns 404."""
    response = authenticated_client.delete("/api/v1/resources/rsc_nonexistent")

    assert response.status_code == 404


def test_delete_resource_permission_denied(authenticated_client, other_user_resource):
    """Test deleting another user's resource returns 403."""
    response = authenticated_client.delete(f"/api/v1/resources/{other_user_resource['id']}")

    assert response.status_code == 403


def test_delete_resource_unauthenticated(client, clean_db):
    """Test deleting a resource without authentication returns 401."""
    response = client.delete("/api/v1/resources/rsc_any_id")

    assert response.status_code == 401


# =============================================================================
# GET /resources/{resource_id}/uploads - List resource uploads
# =============================================================================

def test_list_resource_uploads_empty(authenticated_client, created_resource):
    """Test listing uploads for a resource with no uploads."""
    resource_id = created_resource["id"]

    response = authenticated_client.get(f"/api/v1/resources/{resource_id}/uploads")

    assert response.status_code == 200
    assert response.json() == []


def test_list_resource_uploads_not_found(authenticated_client, clean_db):
    """Test listing uploads for non-existent resource returns 404."""
    response = authenticated_client.get("/api/v1/resources/rsc_nonexistent/uploads")

    assert response.status_code == 404


def test_list_resource_uploads_permission_denied(authenticated_client, other_user_resource):
    """Test listing uploads for another user's resource returns 403."""
    response = authenticated_client.get(f"/api/v1/resources/{other_user_resource['id']}/uploads")

    assert response.status_code == 403


def test_list_resource_uploads_unauthenticated(client, clean_db):
    """Test listing uploads without authentication returns 401."""
    response = client.get("/api/v1/resources/rsc_any_id/uploads")

    assert response.status_code == 401


# =============================================================================
# POST /resources/{resource_id}/ingest - Trigger ingestion
# =============================================================================

@pytest.fixture
def mock_ingestion_pipeline():
    """Mock the entire ingestion pipeline to avoid async background task complexity."""
    with patch('app.core.services.resources.rag.ingestion.ingest_resource', new_callable=AsyncMock) as mock:
        mock.return_value = None
        yield mock


def test_ingest_resource_success(authenticated_client, created_resource, mock_ingestion_pipeline):
    """Test triggering resource ingestion."""
    resource_id = created_resource["id"]

    response = authenticated_client.post(f"/api/v1/resources/{resource_id}/ingest")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
    # Verify ingestion was called with correct resource_id
    mock_ingestion_pipeline.assert_called_once_with(resource_id)


def test_ingest_resource_not_found(authenticated_client, clean_db, mock_ingestion_pipeline):
    """Test ingesting non-existent resource returns 404."""
    response = authenticated_client.post("/api/v1/resources/rsc_nonexistent/ingest")

    assert response.status_code == 404


def test_ingest_resource_permission_denied(authenticated_client, other_user_resource, mock_ingestion_pipeline):
    """Test ingesting another user's resource returns 403."""
    response = authenticated_client.post(f"/api/v1/resources/{other_user_resource['id']}/ingest")

    assert response.status_code == 403


def test_ingest_resource_unauthenticated(client, clean_db, mock_ingestion_pipeline):
    """Test ingesting a resource without authentication returns 401."""
    response = client.post("/api/v1/resources/rsc_any_id/ingest")

    assert response.status_code == 401
