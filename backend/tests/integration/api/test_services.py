"""Integration tests for services routes.

Tests all LLM Service endpoints:
- GET /api/v1/services/providers (list distinct providers)
- POST /api/v1/services (create service)
- GET /api/v1/services (list with filters)
- GET /api/v1/services/{service_id} (get by ID)
- PATCH /api/v1/services/{service_id} (update)
- DELETE /api/v1/services/{service_id} (delete with cascade)
- PATCH /api/v1/services/{service_id}/logo (upload logo)
"""

import pytest
import io


@pytest.fixture
def sample_service(authenticated_client, clean_db):
    """Create a sample service via API.

    Services are core entities for LLM providers.
    """
    response = authenticated_client.post("/api/v1/services", json={
        "name": "Test Service",
        "provider": "openai",
        "description": "Test service for integration tests",
        "status": "active"
    })

    assert response.status_code == 201, f"Service creation failed: {response.text}"
    return response.json()


@pytest.fixture
def other_service(authenticated_client, sample_service):
    """Create another service for filtering tests."""
    response = authenticated_client.post("/api/v1/services", json={
        "name": "Anthropic Service",
        "provider": "anthropic",
        "description": "Claude LLM provider",
        "status": "active"
    })

    assert response.status_code == 201, f"Other service creation failed: {response.text}"
    return response.json()


# =============================================================================
# GET /services/providers - List distinct providers
# =============================================================================

def test_list_providers_empty(authenticated_client, clean_db):
    """Test listing providers when no services exist."""
    response = authenticated_client.get("/api/v1/services/providers")

    assert response.status_code == 200
    assert response.json() == []


def test_list_providers_with_services(authenticated_client, clean_db):
    """Test listing providers with multiple services.

    Fixed: Migrated from get_connection() to get_pool() pattern.
    """
    # Create services with different providers
    resp1 = authenticated_client.post("/api/v1/services", json={
        "name": "OpenAI Service",
        "provider": "openai",
        "status": "active"
    })
    assert resp1.status_code == 201, f"Failed to create OpenAI service: {resp1.text}"

    resp2 = authenticated_client.post("/api/v1/services", json={
        "name": "Anthropic Service",
        "provider": "anthropic",
        "status": "active"
    })
    assert resp2.status_code == 201, f"Failed to create Anthropic service: {resp2.text}"

    response = authenticated_client.get("/api/v1/services/providers")

    assert response.status_code == 200
    providers = response.json()
    assert isinstance(providers, list)
    assert len(providers) >= 2, f"Expected >=2 providers, got {len(providers)}: {providers}"
    assert "openai" in providers
    assert "anthropic" in providers
    # Verify alphabetical ordering
    assert providers == sorted(providers)


def test_list_providers_unauthenticated(client, clean_db):
    """Test listing providers without authentication returns 401."""
    response = client.get("/api/v1/services/providers")

    assert response.status_code == 401


# =============================================================================
# POST /services - Create service
# =============================================================================

def test_create_service_success(authenticated_client, clean_db):
    """Test creating service with valid data."""
    response = authenticated_client.post("/api/v1/services", json={
        "name": "OpenAI GPT",
        "provider": "openai",
        "description": "OpenAI LLM provider",
        "status": "active"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "OpenAI GPT"
    assert data["provider"] == "openai"
    assert data["description"] == "OpenAI LLM provider"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data


def test_create_service_minimal_fields(authenticated_client, clean_db):
    """Test creating service with minimal required fields."""
    response = authenticated_client.post("/api/v1/services", json={
        "name": "Minimal Service",
        "provider": "custom",
        "status": "active"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Service"
    assert data["provider"] == "custom"
    assert data["status"] == "active"


def test_create_service_invalid_data(authenticated_client, clean_db):
    """Test creating service with invalid data returns 422."""
    response = authenticated_client.post("/api/v1/services", json={
        "name": "",  # Empty name should fail validation
        "provider": "openai"
    })

    assert response.status_code == 422


def test_create_service_unauthenticated(client, clean_db):
    """Test creating service without authentication returns 401."""
    response = client.post("/api/v1/services", json={
        "name": "Test Service",
        "provider": "openai",
        "status": "active"
    })

    assert response.status_code == 401


# =============================================================================
# GET /services - List services with filters
# =============================================================================

def test_list_services_empty(authenticated_client, clean_db):
    """Test listing services when database is empty."""
    response = authenticated_client.get("/api/v1/services")

    assert response.status_code == 200
    assert response.json() == []


def test_list_services_with_data(authenticated_client, sample_service, other_service):
    """Test listing all services."""
    response = authenticated_client.get("/api/v1/services")

    assert response.status_code == 200
    services = response.json()
    assert isinstance(services, list)
    assert len(services) >= 2

    # Verify service structure
    service = services[0]
    assert "id" in service
    assert "name" in service
    assert "provider" in service
    assert "status" in service


def test_list_services_filter_by_provider(authenticated_client, sample_service, other_service):
    """Test filtering services by single provider."""
    response = authenticated_client.get("/api/v1/services?provider=openai")

    assert response.status_code == 200
    services = response.json()
    assert len(services) >= 1
    assert all(s["provider"] == "openai" for s in services)


def test_list_services_filter_by_multiple_providers(authenticated_client, sample_service, other_service):
    """Test filtering services by multiple providers (CSV format)."""
    response = authenticated_client.get("/api/v1/services?provider=openai,anthropic")

    assert response.status_code == 200
    services = response.json()
    assert len(services) >= 2
    providers = {s["provider"] for s in services}
    assert "openai" in providers
    assert "anthropic" in providers


def test_list_services_filter_by_status(authenticated_client, clean_db):
    """Test filtering services by status."""
    # Create active service
    authenticated_client.post("/api/v1/services", json={
        "name": "Active Service",
        "provider": "openai",
        "status": "active"
    })

    # Create inactive service
    authenticated_client.post("/api/v1/services", json={
        "name": "Inactive Service",
        "provider": "openai",
        "status": "inactive"
    })

    response = authenticated_client.get("/api/v1/services?status=active")

    assert response.status_code == 200
    services = response.json()
    assert all(s["status"] == "active" for s in services)


def test_list_services_combined_filters(authenticated_client, sample_service, other_service):
    """Test filtering services by provider and status."""
    response = authenticated_client.get("/api/v1/services?provider=openai&status=active")

    assert response.status_code == 200
    services = response.json()
    assert all(s["provider"] == "openai" and s["status"] == "active" for s in services)


def test_list_services_unauthenticated(client, clean_db):
    """Test listing services without authentication returns 401."""
    response = client.get("/api/v1/services")

    assert response.status_code == 401


# =============================================================================
# GET /services/{service_id} - Get by ID
# =============================================================================

def test_get_service_success(authenticated_client, sample_service):
    """Test getting service by ID."""
    response = authenticated_client.get(f"/api/v1/services/{sample_service['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_service["id"]
    assert data["name"] == sample_service["name"]
    assert data["provider"] == sample_service["provider"]


def test_get_service_not_found(authenticated_client, clean_db):
    """Test getting non-existent service returns 404."""
    response = authenticated_client.get("/api/v1/services/svc_nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_service_unauthenticated(client, clean_db):
    """Test getting service without authentication returns 401."""
    response = client.get("/api/v1/services/svc_test")

    assert response.status_code == 401


# =============================================================================
# PATCH /services/{service_id} - Update service
# =============================================================================

def test_update_service_success(authenticated_client, sample_service):
    """Test updating service with full data."""
    response = authenticated_client.patch(
        f"/api/v1/services/{sample_service['id']}",
        json={
            "name": "Updated Service Name",
            "provider": "anthropic",  # Changed to valid provider
            "description": "Updated description",
            "status": "inactive"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_service["id"]
    assert data["name"] == "Updated Service Name"
    assert data["provider"] == "anthropic"
    assert data["description"] == "Updated description"
    assert data["status"] == "inactive"


def test_update_service_partial(authenticated_client, sample_service):
    """Test partial update of service."""
    original_provider = sample_service["provider"]

    response = authenticated_client.patch(
        f"/api/v1/services/{sample_service['id']}",
        json={"name": "Partially Updated"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partially Updated"
    assert data["provider"] == original_provider  # Unchanged


def test_update_service_not_found(authenticated_client, clean_db):
    """Test updating non-existent service returns 404."""
    response = authenticated_client.patch(
        "/api/v1/services/svc_nonexistent",
        json={"name": "Updated"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_service_unauthenticated(client, clean_db):
    """Test updating service without authentication returns 401."""
    response = client.patch(
        "/api/v1/services/svc_test",
        json={"name": "Updated"}
    )

    assert response.status_code == 401


# =============================================================================
# DELETE /services/{service_id} - Delete service
# =============================================================================

def test_delete_service_success(authenticated_client, sample_service):
    """Test deleting service."""
    response = authenticated_client.delete(f"/api/v1/services/{sample_service['id']}")

    assert response.status_code == 204

    # Verify service is deleted
    get_response = authenticated_client.get(f"/api/v1/services/{sample_service['id']}")
    assert get_response.status_code == 404


def test_delete_service_with_cascade(authenticated_client, sample_service):
    """Test deleting service cascades to models.

    Note: This verifies the cascade behavior mentioned in the endpoint docstring.
    """
    # Create a model linked to this service
    from app.core.utils.id_generator import generate_id
    import asyncio
    import asyncpg

    async def create_model():
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="test_backend",
            user="hugohoarau",
            password=""
        )
        await conn.execute("""
            SET search_path TO core, agents, chat, mcp, resources, audit, automation, public
        """)

        model_id = generate_id('model')
        await conn.execute("""
            INSERT INTO models (id, service_id, model_name, display_name, enabled)
            VALUES ($1, $2, $3, $4, $5)
        """, model_id, sample_service['id'], "test-model", "Test Model", True)

        await conn.close()
        return model_id

    model_id = asyncio.run(create_model())

    # Delete service
    response = authenticated_client.delete(f"/api/v1/services/{sample_service['id']}")
    assert response.status_code == 204

    # Verify model is also deleted (cascade)
    async def verify_cascade():
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="test_backend",
            user="hugohoarau",
            password=""
        )
        await conn.execute("""
            SET search_path TO core, agents, chat, mcp, resources, audit, automation, public
        """)

        model = await conn.fetchrow("SELECT * FROM models WHERE id = $1", model_id)
        await conn.close()
        return model

    model = asyncio.run(verify_cascade())
    assert model is None, "Model should be deleted via cascade"


def test_delete_service_not_found(authenticated_client, clean_db):
    """Test deleting non-existent service returns 404."""
    response = authenticated_client.delete("/api/v1/services/svc_nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_service_unauthenticated(client, clean_db):
    """Test deleting service without authentication returns 401."""
    response = client.delete("/api/v1/services/svc_test")

    assert response.status_code == 401


# =============================================================================
# PATCH /services/{service_id}/logo - Upload logo
# =============================================================================

def test_upload_service_logo_success(authenticated_client, sample_service):
    """Test uploading logo for service.

    Requires migration 024 to be applied (adds service_id column to uploads table).
    """
    # Create a fake image file
    fake_image = io.BytesIO(b"fake image content")

    response = authenticated_client.patch(
        f"/api/v1/services/{sample_service['id']}/logo",
        files={"logo": ("test_logo.png", fake_image, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service_id"] == sample_service["id"]
    assert "logo_upload_id" in data
    assert data["message"] == "Logo uploaded successfully"


def test_upload_service_logo_replaces_existing(authenticated_client, sample_service):
    """Test uploading new logo replaces existing one.

    Requires migration 024 to be applied (adds service_id column to uploads table).
    """
    # Upload first logo
    fake_image1 = io.BytesIO(b"first logo")
    response1 = authenticated_client.patch(
        f"/api/v1/services/{sample_service['id']}/logo",
        files={"logo": ("logo1.png", fake_image1, "image/png")}
    )
    assert response1.status_code == 200
    first_upload_id = response1.json()["logo_upload_id"]

    # Upload second logo
    fake_image2 = io.BytesIO(b"second logo")
    response2 = authenticated_client.patch(
        f"/api/v1/services/{sample_service['id']}/logo",
        files={"logo": ("logo2.png", fake_image2, "image/png")}
    )
    assert response2.status_code == 200
    second_upload_id = response2.json()["logo_upload_id"]

    # Verify different upload IDs (old one replaced)
    assert first_upload_id != second_upload_id


def test_upload_service_logo_service_not_found(authenticated_client, clean_db):
    """Test uploading logo for non-existent service returns 404."""
    fake_image = io.BytesIO(b"fake image")

    response = authenticated_client.patch(
        "/api/v1/services/svc_nonexistent/logo",
        files={"logo": ("logo.png", fake_image, "image/png")}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_upload_service_logo_unauthenticated(client, clean_db):
    """Test uploading logo without authentication returns 401."""
    fake_image = io.BytesIO(b"fake image")

    response = client.patch(
        "/api/v1/services/svc_test/logo",
        files={"logo": ("logo.png", fake_image, "image/png")}
    )

    assert response.status_code == 401
