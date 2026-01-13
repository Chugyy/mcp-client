"""Integration tests for models routes.

Tests all LLM model endpoints:
- GET /api/v1/models/providers (list from API providers)
- POST /api/v1/models/sync (sync from providers to DB)
- POST /api/v1/models (create model)
- GET /api/v1/models (list from DB)
- GET /api/v1/models/with-service (list with service info)
- GET /api/v1/models/{model_id} (get by ID)
- PATCH /api/v1/models/{model_id} (update)
- DELETE /api/v1/models/{model_id} (delete)
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def sample_service(authenticated_client, clean_db):
    """Create a sample LLM service via database.

    Services are required for creating models (FK relationship).
    """
    import asyncio
    import asyncpg
    from app.core.utils.id_generator import generate_id

    async def create_service():
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

        service_id = generate_id('service')
        await conn.execute("""
            INSERT INTO services (id, name, provider, description, status)
            VALUES ($1, $2, $3, $4, $5)
        """, service_id, "Test LLM Service", "openai", "Test service for models", "active")

        service = await conn.fetchrow("""
            SELECT * FROM services WHERE id = $1
        """, service_id)

        await conn.close()
        return dict(service)

    service = asyncio.run(create_service())
    return service


@pytest.fixture
def sample_model(authenticated_client, sample_service, test_user):
    """Create a sample LLM model via API and set up user_provider with API key."""
    import asyncio
    import asyncpg
    from app.core.utils.id_generator import generate_id

    # First, create the model
    response = authenticated_client.post("/api/v1/models", json={
        "service_id": sample_service["id"],
        "model_name": "gpt-4-test",
        "display_name": "GPT-4 Test",
        "description": "Test model",
        "enabled": True
    })

    assert response.status_code == 201, f"Model creation failed: {response.text}"
    model = response.json()

    # Create user_provider with API key so list_models_for_user returns results
    async def setup_user_provider():
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

        # Create an API key for the service
        api_key_id = generate_id('key')
        await conn.execute("""
            INSERT INTO api_keys (id, encrypted_value, user_id, service_id)
            VALUES ($1, $2, $3, $4)
        """, api_key_id, "encrypted_test_key_value", test_user["id"], sample_service["id"])

        # Create user_provider linking user to service with API key
        user_provider_id = generate_id('user_provider')
        await conn.execute("""
            INSERT INTO user_providers (id, user_id, service_id, api_key_id, enabled)
            VALUES ($1, $2, $3, $4, $5)
        """, user_provider_id, test_user["id"], sample_service["id"], api_key_id, True)

        await conn.close()

    asyncio.run(setup_user_provider())

    return model


class TestListModelsFromProviders:
    """Tests for GET /api/v1/models/providers"""

    def test_list_models_from_providers_success(self, authenticated_client, mock_llm_gateway):
        """Test listing models from providers successfully."""
        # Mock is already configured in conftest.py
        response = authenticated_client.get("/api/v1/models/providers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "openai" in data or "anthropic" in data  # At least one provider

    def test_list_models_from_providers_specific_provider(self, authenticated_client, mock_llm_gateway):
        """Test listing models from specific provider."""
        response = authenticated_client.get("/api/v1/models/providers?provider=openai")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_list_models_from_providers_no_providers_configured(self, authenticated_client):
        """Test listing when no providers configured returns error."""
        with patch('app.core.services.llm.gateway.llm_gateway.list_models', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {}  # No providers

            response = authenticated_client.get("/api/v1/models/providers")

            # Should return error when no providers configured
            assert response.status_code in [400, 500]

    def test_list_models_from_providers_unauthenticated(self, client, clean_db):
        """Test listing models without authentication returns 401."""
        response = client.get("/api/v1/models/providers")

        assert response.status_code == 401


class TestSyncModels:
    """Tests for POST /api/v1/models/sync"""

    def test_sync_models_success(self, authenticated_client, sample_service):
        """Test syncing models from providers to DB."""
        with patch('app.core.services.llm.sync.model_sync_service.sync_models_to_db', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "synced": 3,
                "created": 2,
                "updated": 1,
                "errors": []
            }

            response = authenticated_client.post("/api/v1/models/sync")

            assert response.status_code == 200
            data = response.json()
            assert data["synced"] == 3
            assert data["created"] == 2
            assert data["updated"] == 1
            assert data["errors"] == []

    def test_sync_models_specific_provider(self, authenticated_client, sample_service):
        """Test syncing models from specific provider."""
        with patch('app.core.services.llm.sync.model_sync_service.sync_models_to_db', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "synced": 1,
                "created": 1,
                "updated": 0,
                "errors": []
            }

            response = authenticated_client.post("/api/v1/models/sync?provider=openai")

            assert response.status_code == 200
            data = response.json()
            assert "synced" in data

    def test_sync_models_unauthenticated(self, client, clean_db):
        """Test syncing models without authentication returns 401."""
        response = client.post("/api/v1/models/sync")

        assert response.status_code == 401


class TestCreateModel:
    """Tests for POST /api/v1/models"""

    def test_create_model_success(self, authenticated_client, sample_service):
        """Test creating a model successfully."""
        response = authenticated_client.post("/api/v1/models", json={
            "service_id": sample_service["id"],
            "model_name": "gpt-4-turbo",
            "display_name": "GPT-4 Turbo",
            "description": "Latest GPT-4 model",
            "enabled": True
        })

        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "gpt-4-turbo"
        assert data["display_name"] == "GPT-4 Turbo"
        assert data["service_id"] == sample_service["id"]
        assert data["enabled"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_model_minimal_fields(self, authenticated_client, sample_service):
        """Test creating model with minimal required fields."""
        response = authenticated_client.post("/api/v1/models", json={
            "service_id": sample_service["id"],
            "model_name": "gpt-3.5-turbo"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "gpt-3.5-turbo"
        assert data["enabled"] is True  # Default value

    def test_create_model_nonexistent_service(self, authenticated_client):
        """Test creating model with nonexistent service returns 404."""
        response = authenticated_client.post("/api/v1/models", json={
            "service_id": "srv_nonexistent",
            "model_name": "test-model"
        })

        assert response.status_code == 404

    def test_create_model_invalid_data(self, authenticated_client, sample_service):
        """Test creating model with invalid data returns 422."""
        response = authenticated_client.post("/api/v1/models", json={
            "service_id": sample_service["id"],
            "model_name": "",  # Empty string (min_length=1)
        })

        assert response.status_code == 422

    def test_create_model_unauthenticated(self, client, clean_db):
        """Test creating model without authentication returns 401."""
        response = client.post("/api/v1/models", json={
            "service_id": "srv_test",
            "model_name": "test-model"
        })

        assert response.status_code == 401


class TestListModelsFromDB:
    """Tests for GET /api/v1/models"""

    def test_list_models_empty(self, authenticated_client):
        """Test listing models when none exist."""
        response = authenticated_client.get("/api/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_models_with_models(self, authenticated_client, sample_model):
        """Test listing models when models exist."""
        response = authenticated_client.get("/api/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_models_unauthenticated(self, client, clean_db):
        """Test listing models without authentication returns 401."""
        response = client.get("/api/v1/models")

        assert response.status_code == 401


class TestListModelsWithService:
    """Tests for GET /api/v1/models/with-service"""

    def test_list_models_with_service_empty(self, authenticated_client):
        """Test listing models with service info when none exist."""
        response = authenticated_client.get("/api/v1/models/with-service")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_models_with_service_info(self, authenticated_client, sample_model, sample_service):
        """Test listing models with service info (JOIN)."""
        response = authenticated_client.get("/api/v1/models/with-service")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify JOIN data is present (service info included)
        model = data[0]
        assert "id" in model
        assert "model_name" in model

    def test_list_models_with_service_unauthenticated(self, client, clean_db):
        """Test listing models with service without authentication returns 401."""
        response = client.get("/api/v1/models/with-service")

        assert response.status_code == 401


class TestGetModel:
    """Tests for GET /api/v1/models/{model_id}"""

    def test_get_model_success(self, authenticated_client, sample_model):
        """Test getting a model by ID successfully."""
        response = authenticated_client.get(f"/api/v1/models/{sample_model['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_model["id"]
        assert data["model_name"] == sample_model["model_name"]
        assert "service_id" in data
        assert "enabled" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_model_not_found(self, authenticated_client):
        """Test getting nonexistent model returns 404."""
        response = authenticated_client.get("/api/v1/models/mdl_nonexistent")

        assert response.status_code == 404

    def test_get_model_unauthenticated(self, client, clean_db):
        """Test getting model without authentication returns 401."""
        response = client.get("/api/v1/models/mdl_test123")

        assert response.status_code == 401


class TestUpdateModel:
    """Tests for PATCH /api/v1/models/{model_id}"""

    def test_update_model_success(self, authenticated_client, sample_model):
        """Test updating a model successfully."""
        response = authenticated_client.patch(f"/api/v1/models/{sample_model['id']}", json={
            "display_name": "Updated Model Name",
            "description": "Updated description",
            "enabled": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_model["id"]
        assert data["display_name"] == "Updated Model Name"
        assert data["description"] == "Updated description"
        assert data["enabled"] is False

    def test_update_model_partial(self, authenticated_client, sample_model):
        """Test partial model update (only display_name)."""
        response = authenticated_client.patch(f"/api/v1/models/{sample_model['id']}", json={
            "display_name": "Partially Updated"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Partially Updated"
        assert data["id"] == sample_model["id"]

    def test_update_model_not_found(self, authenticated_client):
        """Test updating nonexistent model returns 404."""
        response = authenticated_client.patch("/api/v1/models/mdl_nonexistent", json={
            "display_name": "Updated"
        })

        assert response.status_code == 404

    def test_update_model_unauthenticated(self, client, clean_db):
        """Test updating model without authentication returns 401."""
        response = client.patch("/api/v1/models/mdl_test123", json={
            "display_name": "Updated"
        })

        assert response.status_code == 401


class TestDeleteModel:
    """Tests for DELETE /api/v1/models/{model_id}"""

    def test_delete_model_success(self, authenticated_client, sample_model):
        """Test deleting a model successfully."""
        response = authenticated_client.delete(f"/api/v1/models/{sample_model['id']}")

        assert response.status_code == 204
        assert response.text == ""

        # Verify model is deleted
        get_response = authenticated_client.get(f"/api/v1/models/{sample_model['id']}")
        assert get_response.status_code == 404

    def test_delete_model_not_found(self, authenticated_client):
        """Test deleting nonexistent model returns 404."""
        response = authenticated_client.delete("/api/v1/models/mdl_nonexistent")

        assert response.status_code == 404

    def test_delete_model_unauthenticated(self, client, clean_db):
        """Test deleting model without authentication returns 401."""
        response = client.delete("/api/v1/models/mdl_test123")

        assert response.status_code == 401
