"""Integration tests for LLM model synchronization."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.services.llm.gateway import LLMGateway
from app.core.services.llm.adapters.anthropic import AnthropicAdapter
from app.core.services.llm.adapters.openai import OpenAIAdapter


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    with patch('app.core.services.llm.gateway.settings') as mock_settings:
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        yield mock_settings


class TestAnthropicModelFetching:
    """Tests for fetching Anthropic models from API."""

    @pytest.mark.asyncio
    async def test_fetch_anthropic_models_success(self, mock_settings):
        """Test successful fetching of Anthropic models."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            # Mock model objects
            mock_model1 = MagicMock()
            mock_model1.id = "claude-sonnet-4-5-20250929"
            mock_model1.type = "model"
            mock_model1.display_name = "Claude Sonnet 4.5"
            mock_model1.created_at = "2025-01-01T00:00:00Z"

            mock_model2 = MagicMock()
            mock_model2.id = "claude-opus-4-5"
            mock_model2.type = "model"
            mock_model2.display_name = "Claude Opus 4.5"
            mock_model2.created_at = "2025-01-01T00:00:00Z"

            mock_response = MagicMock()
            mock_response.data = [mock_model1, mock_model2]

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify models fetched
            assert len(models) == 2
            assert models[0]["id"] == "claude-sonnet-4-5-20250929"
            assert models[0]["provider"] == "Anthropic"
            assert models[0]["display_name"] == "Claude Sonnet 4.5"
            assert models[1]["id"] == "claude-opus-4-5"

    @pytest.mark.asyncio
    async def test_fetch_anthropic_models_with_metadata(self, mock_settings):
        """Test fetched models include all required metadata."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            mock_model = MagicMock()
            mock_model.id = "claude-sonnet-4"
            mock_model.type = "model"
            mock_model.display_name = "Claude Sonnet 4"
            mock_model.created_at = "2024-12-01T00:00:00Z"

            mock_response = MagicMock()
            mock_response.data = [mock_model]

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify all metadata fields present
            assert "id" in models[0]
            assert "type" in models[0]
            assert "display_name" in models[0]
            assert "created_at" in models[0]
            assert "provider" in models[0]

    @pytest.mark.asyncio
    async def test_fetch_anthropic_models_fallback_on_error(self, mock_settings):
        """Test fallback to hardcoded models on API error."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.models.list.side_effect = Exception("API unavailable")
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Should return hardcoded fallback list
            assert len(models) > 0
            assert all(m["provider"] == "Anthropic" for m in models)
            # Verify hardcoded models present
            model_ids = [m["id"] for m in models]
            assert "claude-sonnet-4-5-20250929" in model_ids


class TestOpenAIModelFetching:
    """Tests for fetching OpenAI models from API."""

    @pytest.mark.asyncio
    async def test_fetch_openai_models_success(self, mock_settings):
        """Test successful fetching of OpenAI models."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            # Mock model objects
            mock_model1 = MagicMock()
            mock_model1.id = "gpt-4o"
            mock_model1.object = "model"
            mock_model1.created = 1704067200
            mock_model1.owned_by = "openai"

            mock_model2 = MagicMock()
            mock_model2.id = "gpt-3.5-turbo"
            mock_model2.object = "model"
            mock_model2.created = 1704067200
            mock_model2.owned_by = "openai"

            # Mock non-chat model (should be filtered)
            mock_model3 = MagicMock()
            mock_model3.id = "text-embedding-ada-002"
            mock_model3.object = "model"
            mock_model3.created = 1704067200
            mock_model3.owned_by = "openai"

            async def mock_list():
                yield mock_model1
                yield mock_model2
                yield mock_model3

            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = mock_list()

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify only chat models returned (filtered)
            assert len(models) == 2
            model_ids = [m["id"] for m in models]
            assert "gpt-4o" in model_ids
            assert "gpt-3.5-turbo" in model_ids
            assert "text-embedding-ada-002" not in model_ids

    @pytest.mark.asyncio
    async def test_fetch_openai_models_with_display_names(self, mock_settings):
        """Test fetched models include generated display names."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            mock_model = MagicMock()
            mock_model.id = "gpt-4o-mini"
            mock_model.object = "model"
            mock_model.created = 1704067200
            mock_model.owned_by = "openai"

            async def mock_list():
                yield mock_model

            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = mock_list()

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify display_name generated
            assert models[0]["display_name"] == "GPT 4O Mini"


class TestGatewayModelSync:
    """Tests for gateway model synchronization."""

    @pytest.mark.asyncio
    async def test_gateway_list_all_provider_models(self, mock_settings):
        """Test gateway fetches models from all providers."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_anthropic_class, \
             patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_openai_class:

            # Mock Anthropic
            mock_anthropic_client = AsyncMock()
            mock_anthropic_model = MagicMock()
            mock_anthropic_model.id = "claude-sonnet-4"
            mock_anthropic_model.type = "model"
            mock_anthropic_model.display_name = "Claude Sonnet 4"
            mock_anthropic_model.created_at = "2024-01-01"

            mock_anthropic_response = MagicMock()
            mock_anthropic_response.data = [mock_anthropic_model]
            mock_anthropic_client.models.list.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_anthropic_client

            # Mock OpenAI
            mock_openai_client = AsyncMock()
            mock_openai_model = MagicMock()
            mock_openai_model.id = "gpt-4o"
            mock_openai_model.object = "model"
            mock_openai_model.created = 1704067200
            mock_openai_model.owned_by = "openai"

            async def mock_openai_list():
                yield mock_openai_model

            mock_openai_response = AsyncMock()
            mock_openai_response.__aiter__.return_value = mock_openai_list()
            mock_openai_client.models.list.return_value = mock_openai_response
            mock_openai_class.return_value = mock_openai_client

            gateway = LLMGateway()

            results = await gateway.list_models()

            # Verify both providers returned
            assert "openai" in results
            assert "anthropic" in results
            assert len(results["openai"]) == 1
            assert len(results["anthropic"]) == 1
            assert results["openai"][0]["id"] == "gpt-4o"
            assert results["anthropic"][0]["id"] == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_gateway_handles_provider_failures_gracefully(self, mock_settings):
        """Test gateway continues if one provider fails."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_anthropic_class, \
             patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_openai_class:

            # Anthropic succeeds
            mock_anthropic_client = AsyncMock()
            mock_anthropic_model = MagicMock()
            mock_anthropic_model.id = "claude-sonnet-4"
            mock_anthropic_model.type = "model"
            mock_anthropic_model.display_name = "Claude Sonnet 4"
            mock_anthropic_model.created_at = "2024-01-01"

            mock_anthropic_response = MagicMock()
            mock_anthropic_response.data = [mock_anthropic_model]
            mock_anthropic_client.models.list.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_anthropic_client

            # OpenAI fails
            mock_openai_client = AsyncMock()
            mock_openai_client.models.list.side_effect = Exception("OpenAI API error")
            mock_openai_class.return_value = mock_openai_client

            gateway = LLMGateway()

            results = await gateway.list_models()

            # Should still return Anthropic models, OpenAI empty
            assert results["anthropic"][0]["id"] == "claude-sonnet-4"
            assert results["openai"] == []


class TestModelListFiltering:
    """Tests for model list filtering."""

    @pytest.mark.asyncio
    async def test_openai_filters_chat_models_only(self, mock_settings):
        """Test OpenAI adapter filters to only chat models."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            # Mix of chat and non-chat models
            models = []

            # Chat models
            gpt4 = MagicMock()
            gpt4.id = "gpt-4"
            gpt4.object = "model"
            gpt4.created = 1
            gpt4.owned_by = "openai"
            models.append(gpt4)

            gpt35 = MagicMock()
            gpt35.id = "gpt-3.5-turbo"
            gpt35.object = "model"
            gpt35.created = 1
            gpt35.owned_by = "openai"
            models.append(gpt35)

            # Non-chat models (should be filtered out)
            embedding = MagicMock()
            embedding.id = "text-embedding-ada-002"
            embedding.object = "model"
            embedding.created = 1
            embedding.owned_by = "openai"
            models.append(embedding)

            whisper = MagicMock()
            whisper.id = "whisper-1"
            whisper.object = "model"
            whisper.created = 1
            whisper.owned_by = "openai"
            models.append(whisper)

            async def mock_list():
                for m in models:
                    yield m

            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = mock_list()

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            chat_models = await adapter.list_models()

            # Should only have chat models
            model_ids = [m["id"] for m in chat_models]
            assert "gpt-4" in model_ids
            assert "gpt-3.5-turbo" in model_ids
            assert "text-embedding-ada-002" not in model_ids
            assert "whisper-1" not in model_ids


class TestModelMetadataCompleteness:
    """Tests for model metadata completeness."""

    @pytest.mark.asyncio
    async def test_anthropic_model_metadata_complete(self, mock_settings):
        """Test Anthropic models have all required metadata."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()

            mock_model = MagicMock()
            mock_model.id = "test-model-id"
            mock_model.type = "model"
            mock_model.display_name = "Test Model"
            mock_model.created_at = "2024-01-01T00:00:00Z"

            mock_response = MagicMock()
            mock_response.data = [mock_model]

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = AnthropicAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify all required fields
            required_fields = ["id", "type", "display_name", "created_at", "provider"]
            for field in required_fields:
                assert field in models[0], f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_openai_model_metadata_complete(self, mock_settings):
        """Test OpenAI models have all required metadata."""
        with patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()

            mock_model = MagicMock()
            mock_model.id = "gpt-4o"
            mock_model.object = "model"
            mock_model.created = 1704067200
            mock_model.owned_by = "openai"

            async def mock_list():
                yield mock_model

            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = mock_list()

            mock_client.models.list.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = OpenAIAdapter(api_key="test-key")
            adapter.client = mock_client

            models = await adapter.list_models()

            # Verify all required fields
            required_fields = ["id", "object", "created", "owned_by", "provider", "display_name"]
            for field in required_fields:
                assert field in models[0], f"Missing required field: {field}"


class TestModelSyncPerformance:
    """Tests for model sync performance."""

    @pytest.mark.asyncio
    async def test_gateway_syncs_providers_concurrently(self, mock_settings):
        """Test gateway fetches models from providers concurrently."""
        with patch('app.core.services.llm.adapters.anthropic.AsyncAnthropic') as mock_anthropic_class, \
             patch('app.core.services.llm.adapters.openai.AsyncOpenAI') as mock_openai_class:

            # Track call times
            import asyncio

            anthropic_called = asyncio.Event()
            openai_called = asyncio.Event()

            async def anthropic_list():
                anthropic_called.set()
                # Wait a bit to ensure concurrent execution
                await asyncio.sleep(0.01)
                mock_model = MagicMock()
                mock_model.id = "claude"
                mock_model.type = "model"
                mock_model.display_name = "Claude"
                mock_model.created_at = "2024-01-01"
                mock_response = MagicMock()
                mock_response.data = [mock_model]
                return mock_response

            async def openai_list():
                openai_called.set()
                await asyncio.sleep(0.01)

                mock_model = MagicMock()
                mock_model.id = "gpt-4"
                mock_model.object = "model"
                mock_model.created = 1
                mock_model.owned_by = "openai"

                async def mock_iter():
                    yield mock_model

                mock_response = AsyncMock()
                mock_response.__aiter__.return_value = mock_iter()
                return mock_response

            mock_anthropic_client = AsyncMock()
            mock_anthropic_client.models.list = anthropic_list
            mock_anthropic_class.return_value = mock_anthropic_client

            mock_openai_client = AsyncMock()
            mock_openai_client.models.list = openai_list
            mock_openai_class.return_value = mock_openai_client

            gateway = LLMGateway()

            # Both should be called during list_models
            results = await gateway.list_models()

            # Verify both were called (no sequential blocking)
            assert anthropic_called.is_set()
            assert openai_called.is_set()
            assert len(results["anthropic"]) > 0
            assert len(results["openai"]) > 0
