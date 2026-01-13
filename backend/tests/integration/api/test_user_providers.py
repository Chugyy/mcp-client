"""Integration tests for User Providers routes.

Tests all User Provider endpoints:
- POST /api/v1/providers (create/link provider)
- GET /api/v1/providers (list user's providers with service info)
- GET /api/v1/providers/{provider_id} (get by ID)
- PATCH /api/v1/providers/{provider_id} (update)
- DELETE /api/v1/providers/{provider_id} (unlink/delete)
"""

import pytest


@pytest.fixture
def sample_service(authenticated_client, clean_db):
    """Create a sample service for user provider tests.

    User providers require a valid service_id to link.
    """
    response = authenticated_client.post("/api/v1/services", json={
        "name": "OpenAI Service",
        "provider": "openai",
        "description": "OpenAI LLM service",
        "status": "active"
    })

    assert response.status_code == 201, f"Service creation failed: {response.text}"
    return response.json()


@pytest.fixture
def second_service(authenticated_client, clean_db):
    """Create a second service for multi-provider tests."""
    response = authenticated_client.post("/api/v1/services", json={
        "name": "Anthropic Service",
        "provider": "anthropic",
        "description": "Anthropic Claude service",
        "status": "active"
    })

    assert response.status_code == 201, f"Second service creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_api_key(authenticated_client, sample_service):
    """Create a sample API key for user provider tests."""
    response = authenticated_client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-test-key-1234567890"
    })

    assert response.status_code == 201, f"API key creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_user_provider(authenticated_client, sample_service, sample_api_key):
    """Create a sample user provider via API.

    Returns the user provider dict from creation response.
    """
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": sample_api_key["id"],
        "enabled": True
    })

    assert response.status_code == 201, f"User provider creation failed: {response.text}"
    return response.json()


@pytest.fixture
def other_user_provider(client, clean_db, sample_service, test_user):
    """Create a user provider belonging to a different user.

    This fixture creates a second user and a provider for them,
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

    # Create an API key for the other user
    api_key_response = client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-other-key-1234567890"
    })
    assert api_key_response.status_code == 201
    api_key_data = api_key_response.json()

    # Create a user provider as the other user
    provider_response = client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": api_key_data["id"],
        "enabled": True
    })
    assert provider_response.status_code == 201

    provider_data = provider_response.json()

    # CRITICAL: Restore original user's cookies for authenticated_client
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    return provider_data


# =============================================================================
# POST /providers - Create user provider (link service)
# =============================================================================

def test_create_user_provider_success(authenticated_client, sample_service, sample_api_key):
    """Test creating a user provider with valid data."""
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": sample_api_key["id"],
        "enabled": True
    })

    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == sample_service["id"]
    assert data["api_key_id"] == sample_api_key["id"]
    assert data["enabled"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_user_provider_minimal(authenticated_client, sample_service):
    """Test creating a user provider with minimal fields (no API key)."""
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "enabled": False
    })

    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == sample_service["id"]
    assert data["api_key_id"] is None
    assert data["enabled"] is False


def test_create_user_provider_nonexistent_service(authenticated_client):
    """Test creating a user provider with nonexistent service returns 404."""
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": "srv_nonexistent123",
        "enabled": True
    })

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_user_provider_nonexistent_api_key(authenticated_client, sample_service):
    """Test creating a user provider with nonexistent API key returns 404."""
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": "key_nonexistent123",
        "enabled": True
    })

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_user_provider_other_users_api_key(authenticated_client, sample_service, client, test_user):
    """Test creating a user provider with another user's API key returns 403."""
    # Create a second user and their API key
    register_response = client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "name": "Other User"
    })
    assert register_response.status_code == 201

    login_response = client.post("/api/v1/auth/login", json={
        "email": "other@example.com",
        "password": "otherpass123"
    })
    assert login_response.status_code == 200

    api_key_response = client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-other-key-1234567890"
    })
    assert api_key_response.status_code == 201
    other_api_key_id = api_key_response.json()["id"]

    # Restore original user session
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    # Try to create provider with other user's API key
    response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": other_api_key_id,
        "enabled": True
    })

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower() or "not belong" in response.json()["detail"].lower()


def test_create_user_provider_duplicate_service(authenticated_client, sample_service, sample_api_key):
    """Test creating duplicate user provider for same service returns 400."""
    # Create first provider
    response1 = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": sample_api_key["id"],
        "enabled": True
    })
    assert response1.status_code == 201

    # Try to create second provider for same service
    response2 = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "enabled": False
    })

    assert response2.status_code == 400
    assert "already configured" in response2.json()["detail"].lower()


def test_create_user_provider_unauthenticated(client, clean_db):
    """Test creating a user provider without authentication returns 401."""
    response = client.post("/api/v1/providers", json={
        "service_id": "srv_test123",
        "enabled": True
    })

    assert response.status_code == 401


# =============================================================================
# GET /providers - List user providers
# =============================================================================

def test_list_user_providers_empty(authenticated_client, clean_db):
    """Test listing user providers when user has no providers."""
    response = authenticated_client.get("/api/v1/providers")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_user_providers_with_providers(authenticated_client, sample_service, second_service, sample_api_key):
    """Test listing user providers returns all user's providers."""
    # Create two providers
    provider1_response = authenticated_client.post("/api/v1/providers", json={
        "service_id": sample_service["id"],
        "api_key_id": sample_api_key["id"],
        "enabled": True
    })
    assert provider1_response.status_code == 201

    provider2_response = authenticated_client.post("/api/v1/providers", json={
        "service_id": second_service["id"],
        "enabled": False
    })
    assert provider2_response.status_code == 201

    # List providers
    response = authenticated_client.get("/api/v1/providers")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Verify basic provider fields
    service_ids = [p["service_id"] for p in data]
    assert sample_service["id"] in service_ids
    assert second_service["id"] in service_ids

    # Verify one provider has API key, other doesn't
    providers_by_service = {p["service_id"]: p for p in data}
    assert providers_by_service[sample_service["id"]]["api_key_id"] == sample_api_key["id"]
    assert providers_by_service[sample_service["id"]]["enabled"] is True
    assert providers_by_service[second_service["id"]]["api_key_id"] is None
    assert providers_by_service[second_service["id"]]["enabled"] is False


def test_list_user_providers_filters_other_users(authenticated_client, other_user_provider, sample_user_provider):
    """Test listing user providers only returns current user's providers, not others."""
    response = authenticated_client.get("/api/v1/providers")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Should only see own provider, not other user's
    provider_ids = [p["id"] for p in data]
    assert sample_user_provider["id"] in provider_ids
    assert other_user_provider["id"] not in provider_ids


def test_list_user_providers_unauthenticated(client):
    """Test listing user providers without authentication returns 401."""
    response = client.get("/api/v1/providers")

    assert response.status_code == 401


# =============================================================================
# GET /providers/{provider_id} - Get user provider by ID
# =============================================================================

def test_get_user_provider_success(authenticated_client, sample_user_provider):
    """Test getting a user provider by ID."""
    response = authenticated_client.get(f"/api/v1/providers/{sample_user_provider['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_user_provider["id"]
    assert data["service_id"] == sample_user_provider["service_id"]
    assert "created_at" in data
    assert "updated_at" in data


def test_get_user_provider_not_found(authenticated_client):
    """Test getting a nonexistent user provider returns 404."""
    response = authenticated_client.get("/api/v1/providers/upr_nonexistent123")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_user_provider_permission_denied(authenticated_client, other_user_provider):
    """Test getting another user's provider returns 403."""
    response = authenticated_client.get(f"/api/v1/providers/{other_user_provider['id']}")

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_get_user_provider_unauthenticated(client, clean_db):
    """Test getting a user provider without authentication returns 401."""
    response = client.get("/api/v1/providers/upr_test123")

    assert response.status_code == 401


# =============================================================================
# PATCH /providers/{provider_id} - Update user provider
# =============================================================================

def test_update_user_provider_success(authenticated_client, sample_user_provider, sample_api_key):
    """Test updating a user provider with new values."""
    response = authenticated_client.patch(
        f"/api/v1/providers/{sample_user_provider['id']}",
        json={
            "enabled": False,
            "api_key_id": sample_api_key["id"]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_user_provider["id"]
    assert data["enabled"] is False
    assert data["api_key_id"] == sample_api_key["id"]


def test_update_user_provider_partial(authenticated_client, sample_user_provider):
    """Test partially updating a user provider (only enabled field)."""
    response = authenticated_client.patch(
        f"/api/v1/providers/{sample_user_provider['id']}",
        json={
            "enabled": False
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    # api_key_id should remain unchanged
    assert data["api_key_id"] == sample_user_provider["api_key_id"]


def test_update_user_provider_not_found(authenticated_client):
    """Test updating a nonexistent user provider returns 404."""
    response = authenticated_client.patch(
        "/api/v1/providers/upr_nonexistent123",
        json={"enabled": False}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_user_provider_permission_denied(authenticated_client, other_user_provider):
    """Test updating another user's provider returns 403."""
    response = authenticated_client.patch(
        f"/api/v1/providers/{other_user_provider['id']}",
        json={"enabled": False}
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_update_user_provider_nonexistent_api_key(authenticated_client, sample_user_provider):
    """Test updating with nonexistent API key returns 404."""
    response = authenticated_client.patch(
        f"/api/v1/providers/{sample_user_provider['id']}",
        json={"api_key_id": "key_nonexistent123"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_user_provider_other_users_api_key(authenticated_client, sample_user_provider, client, test_user, sample_service):
    """Test updating with another user's API key returns 403."""
    # Create a second user and their API key
    register_response = client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "name": "Other User"
    })
    assert register_response.status_code == 201

    login_response = client.post("/api/v1/auth/login", json={
        "email": "other@example.com",
        "password": "otherpass123"
    })
    assert login_response.status_code == 200

    api_key_response = client.post("/api/v1/api-keys", json={
        "service_id": sample_service["id"],
        "plain_value": "sk-other-key-1234567890"
    })
    assert api_key_response.status_code == 201
    other_api_key_id = api_key_response.json()["id"]

    # Restore original user session
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    # Try to update with other user's API key
    response = authenticated_client.patch(
        f"/api/v1/providers/{sample_user_provider['id']}",
        json={"api_key_id": other_api_key_id}
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower() or "not belong" in response.json()["detail"].lower()


def test_update_user_provider_unauthenticated(client, clean_db):
    """Test updating a user provider without authentication returns 401."""
    response = client.patch(
        "/api/v1/providers/upr_test123",
        json={"enabled": False}
    )

    assert response.status_code == 401


# =============================================================================
# DELETE /providers/{provider_id} - Delete user provider
# =============================================================================

def test_delete_user_provider_success(authenticated_client, sample_user_provider):
    """Test deleting a user provider."""
    response = authenticated_client.delete(f"/api/v1/providers/{sample_user_provider['id']}")

    assert response.status_code == 204

    # Verify deletion
    get_response = authenticated_client.get(f"/api/v1/providers/{sample_user_provider['id']}")
    assert get_response.status_code == 404


def test_delete_user_provider_not_found(authenticated_client):
    """Test deleting a nonexistent user provider returns 404."""
    response = authenticated_client.delete("/api/v1/providers/upr_nonexistent123")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_user_provider_permission_denied(authenticated_client, other_user_provider):
    """Test deleting another user's provider returns 403."""
    response = authenticated_client.delete(f"/api/v1/providers/{other_user_provider['id']}")

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_delete_user_provider_unauthenticated(client, clean_db):
    """Test deleting a user provider without authentication returns 401."""
    response = client.delete("/api/v1/providers/upr_test123")

    assert response.status_code == 401
