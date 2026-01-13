"""Integration tests for API Keys routes.

Tests all API Key endpoints:
- POST /api/v1/api-keys (create with encryption)
- GET /api/v1/api-keys (list user's API keys)
- GET /api/v1/api-keys/{key_id} (get by ID)
- PATCH /api/v1/api-keys/{key_id} (update/rotation)
- DELETE /api/v1/api-keys/{key_id} (delete)
"""

import pytest


@pytest.fixture
def sample_service(authenticated_client, clean_db):
    """Create a sample service for API key tests.

    API keys require a valid service_id to be created.
    """
    response = authenticated_client.post("/api/v1/services", json={
        "name": "Test Service",
        "provider": "openai",
        "description": "Test service for API key tests",
        "status": "active"
    })

    assert response.status_code == 201, f"Service creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_api_key(authenticated_client, sample_service):
    """Create a sample API key via API.

    Returns the API key dict WITHOUT plain_value (as only creation returns it).
    """
    response = authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-test-1234567890abcdef"
    })

    assert response.status_code == 201, f"API key creation failed: {response.text}"
    data = response.json()
    # Remove plain_value as it's only returned at creation
    return {
        "id": data["id"],
        "service_id": data["service_id"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"]
    }


@pytest.fixture
def other_user_api_key(client, clean_db, sample_service, test_user):
    """Create an API key belonging to a different user.

    This fixture creates a second user and an API key for them,
    useful for testing authorization and permission checks.
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

    # Create an API key as the other user
    api_key_response = client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-other-1234567890abcdef"
    })
    assert api_key_response.status_code == 201

    api_key_data = api_key_response.json()

    # CRITICAL: Restore original user's cookies for authenticated_client
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    return {
        "id": api_key_data["id"],
        "service_id": api_key_data["service_id"],
        "created_at": api_key_data["created_at"],
        "updated_at": api_key_data["updated_at"]
    }


# =============================================================================
# POST /api-keys - Create API key
# =============================================================================

def test_create_api_key_success(authenticated_client, sample_service):
    """Test creating API key with valid data.

    IMPORTANT: Plain value is only returned at creation time.
    """
    response = authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-test-abcdef123456"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == sample_service["id"]
    assert data["plain_value"] == "sk-test-abcdef123456"  # Only at creation
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_api_key_service_not_found(authenticated_client, clean_db):
    """Test creating API key with non-existent service returns 404."""
    response = authenticated_client.post("/api/v1/api-keys", json={
        "service_id": "svc_nonexistent",
        "plain_value": "sk-test-abcdef123456"
    })

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_api_key_invalid_data(authenticated_client, sample_service):
    """Test creating API key with invalid data returns 422."""
    response = authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": ""  # Empty plain_value should fail validation
    })

    assert response.status_code == 422


def test_create_api_key_missing_service_id(authenticated_client, clean_db):
    """Test creating API key without service_id returns 422."""
    response = authenticated_client.post("/api/v1/api-keys", json={
        "plain_value": "sk-test-abcdef123456"
    })

    assert response.status_code == 422


def test_create_api_key_unauthenticated(client, clean_db):
    """Test creating API key without authentication returns 401."""
    response = client.post("/api/v1/api-keys", json={
        "service_id": "svc_test",
        "plain_value": "sk-test-abcdef123456"
    })

    assert response.status_code == 401


# =============================================================================
# GET /api-keys - List API keys
# =============================================================================

def test_list_api_keys_empty(authenticated_client, clean_db):
    """Test listing API keys when user has none."""
    response = authenticated_client.get("/api/v1/api-keys")

    assert response.status_code == 200
    assert response.json() == []


def test_list_api_keys_with_data(authenticated_client, sample_service, clean_db):
    """Test listing API keys.

    IMPORTANT: plain_value is NOT returned in list endpoint.
    """
    # Create multiple API keys
    authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-test-key1"
    })
    authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-test-key2"
    })

    response = authenticated_client.get("/api/v1/api-keys")

    assert response.status_code == 200
    api_keys = response.json()
    assert isinstance(api_keys, list)
    assert len(api_keys) >= 2

    # Verify structure (no plain_value)
    api_key = api_keys[0]
    assert "id" in api_key
    assert "service_id" in api_key
    assert "created_at" in api_key
    assert "updated_at" in api_key
    assert "plain_value" not in api_key  # Security: never expose in list


def test_list_api_keys_filters_by_user(authenticated_client, sample_api_key, other_user_api_key):
    """Test listing API keys only returns current user's keys."""
    response = authenticated_client.get("/api/v1/api-keys")

    assert response.status_code == 200
    api_keys = response.json()

    # Should only see own key, not other user's key
    api_key_ids = [k["id"] for k in api_keys]
    assert sample_api_key["id"] in api_key_ids
    assert other_user_api_key["id"] not in api_key_ids


def test_list_api_keys_unauthenticated(client, clean_db):
    """Test listing API keys without authentication returns 401."""
    response = client.get("/api/v1/api-keys")

    assert response.status_code == 401


# =============================================================================
# GET /api-keys/{key_id} - Get by ID
# =============================================================================

def test_get_api_key_success(authenticated_client, sample_api_key):
    """Test getting API key by ID.

    IMPORTANT: plain_value is NOT returned (security).
    """
    response = authenticated_client.get(f"/api/v1/api-keys/{sample_api_key['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_api_key["id"]
    assert data["service_id"] == sample_api_key["service_id"]
    assert "plain_value" not in data  # Security: never expose


def test_get_api_key_not_found(authenticated_client, clean_db):
    """Test getting non-existent API key returns 404."""
    response = authenticated_client.get("/api/v1/api-keys/key_nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_api_key_permission_denied(authenticated_client, other_user_api_key):
    """Test getting other user's API key returns 403."""
    response = authenticated_client.get(f"/api/v1/api-keys/{other_user_api_key['id']}")

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_get_api_key_unauthenticated(client, clean_db):
    """Test getting API key without authentication returns 401."""
    response = client.get("/api/v1/api-keys/key_test")

    assert response.status_code == 401


# =============================================================================
# PATCH /api-keys/{key_id} - Update API key (rotation)
# =============================================================================

def test_update_api_key_success(authenticated_client, sample_api_key):
    """Test updating API key (key rotation).

    API key updates are used for rotating the encrypted value.
    """
    response = authenticated_client.patch(
        f"/api/v1/api-keys/{sample_api_key['id']}",
        json={"plain_value": "sk-test-rotated-newkey"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_api_key["id"]
    assert data["service_id"] == sample_api_key["service_id"]
    assert "plain_value" not in data  # Security: not returned after rotation


def test_update_api_key_not_found(authenticated_client, clean_db):
    """Test updating non-existent API key returns 404."""
    response = authenticated_client.patch(
        "/api/v1/api-keys/key_nonexistent",
        json={"plain_value": "sk-test-newvalue"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_api_key_permission_denied(authenticated_client, other_user_api_key):
    """Test updating other user's API key returns 403."""
    response = authenticated_client.patch(
        f"/api/v1/api-keys/{other_user_api_key['id']}",
        json={"plain_value": "sk-test-hacked"}
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_update_api_key_invalid_data(authenticated_client, sample_api_key):
    """Test updating API key with invalid data returns 422."""
    response = authenticated_client.patch(
        f"/api/v1/api-keys/{sample_api_key['id']}",
        json={"plain_value": ""}  # Empty value should fail
    )

    assert response.status_code == 422


def test_update_api_key_unauthenticated(client, clean_db):
    """Test updating API key without authentication returns 401."""
    response = client.patch(
        "/api/v1/api-keys/key_test",
        json={"plain_value": "sk-test-newvalue"}
    )

    assert response.status_code == 401


# =============================================================================
# DELETE /api-keys/{key_id} - Delete API key
# =============================================================================

def test_delete_api_key_success(authenticated_client, sample_api_key):
    """Test deleting API key."""
    response = authenticated_client.delete(f"/api/v1/api-keys/{sample_api_key['id']}")

    assert response.status_code == 204

    # Verify API key is deleted
    get_response = authenticated_client.get(f"/api/v1/api-keys/{sample_api_key['id']}")
    assert get_response.status_code == 404


def test_delete_api_key_not_found(authenticated_client, clean_db):
    """Test deleting non-existent API key returns 404."""
    response = authenticated_client.delete("/api/v1/api-keys/key_nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_api_key_permission_denied(authenticated_client, other_user_api_key):
    """Test deleting other user's API key returns 403."""
    response = authenticated_client.delete(f"/api/v1/api-keys/{other_user_api_key['id']}")

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_delete_api_key_unauthenticated(client, clean_db):
    """Test deleting API key without authentication returns 401."""
    response = client.delete("/api/v1/api-keys/key_test")

    assert response.status_code == 401
