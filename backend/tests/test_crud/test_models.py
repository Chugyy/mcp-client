"""Integration tests for models (LLM) CRUD module."""

import pytest
from app.database.crud import models



@pytest.mark.asyncio
async def test_create_model(clean_db, sample_service, mock_pool_for_crud):
    """Test creating an LLM model."""
    model_id = await models.create_model(
        service_id=sample_service["id"],
        model_name="gpt-4",
        display_name="GPT-4",
        description="OpenAI GPT-4 model"
    )

    assert model_id is not None
    assert model_id.startswith("mdl_")

    model = await models.get_model(model_id)
    assert model["model_name"] == "gpt-4"
    assert model["display_name"] == "GPT-4"


@pytest.mark.asyncio
async def test_get_model_by_name(clean_db, sample_service, mock_pool_for_crud):
    """Test getting model by name."""
    model_id = await models.create_model(
        service_id=sample_service["id"],
        model_name="claude-3-opus"
    )

    model = await models.get_model(model_id)
    assert model is not None
    assert model["model_name"] == "claude-3-opus"


@pytest.mark.asyncio
async def test_update_model_parameters(clean_db, sample_service, mock_pool_for_crud):
    """Test updating model parameters."""
    model_id = await models.create_model(
        service_id=sample_service["id"],
        model_name="test-model"
    )

    success = await models.update_model(
        model_id,
        display_name="Updated Model",
        description="Updated description"
    )
    assert success is True

    model = await models.get_model(model_id)
    assert model["display_name"] == "Updated Model"


@pytest.mark.asyncio
async def test_delete_model(clean_db, sample_service, mock_pool_for_crud):
    """Test deleting a model."""
    model_id = await models.create_model(
        service_id=sample_service["id"],
        model_name="temp-model"
    )

    success = await models.delete_model(model_id)
    assert success is True

    model = await models.get_model(model_id)
    assert model is None


@pytest.mark.asyncio
async def test_list_models_by_provider(clean_db, sample_service, mock_pool_for_crud):
    """Test listing models filtered by provider/service."""
    model1_id = await models.create_model(
        service_id=sample_service["id"],
        model_name="model-1"
    )

    models_list = await models.list_models(service_id=sample_service["id"])
    assert any(m["id"] == model1_id for m in models_list)
