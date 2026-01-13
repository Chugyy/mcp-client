"""Unit tests for LLM Gateway."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.services.llm.gateway import LLMGateway
from app.core.services.llm.types import ToolDefinition, ToolCall, ToolResult


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    with patch('app.core.services.llm.gateway.settings') as mock_settings:
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        yield mock_settings


@pytest.fixture
def llm_gateway(mock_settings):
    """Create LLM gateway with mocked adapters."""
    with patch('app.core.services.llm.gateway.OpenAIAdapter') as mock_openai, \
         patch('app.core.services.llm.gateway.AnthropicAdapter') as mock_anthropic:

        mock_openai_instance = AsyncMock()
        mock_anthropic_instance = AsyncMock()

        mock_openai.return_value = mock_openai_instance
        mock_anthropic.return_value = mock_anthropic_instance

        gateway = LLMGateway()

        # Replace adapters with mocks
        gateway.adapters["openai"] = mock_openai_instance
        gateway.adapters["anthropic"] = mock_anthropic_instance

        yield gateway, mock_openai_instance, mock_anthropic_instance


class TestGatewayInitialization:
    """Tests for gateway initialization."""

    def test_init_with_api_keys(self, mock_settings):
        """Test gateway initializes adapters when API keys present."""
        with patch('app.core.services.llm.gateway.OpenAIAdapter') as mock_openai, \
             patch('app.core.services.llm.gateway.AnthropicAdapter') as mock_anthropic:

            gateway = LLMGateway()

            # Should initialize both adapters
            mock_openai.assert_called_once_with("test-openai-key")
            mock_anthropic.assert_called_once_with("test-anthropic-key")
            assert "openai" in gateway.adapters
            assert "anthropic" in gateway.adapters

    def test_init_without_api_keys(self):
        """Test gateway handles missing API keys."""
        with patch('app.core.services.llm.gateway.settings') as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.anthropic_api_key = None

            gateway = LLMGateway()

            # Should have no adapters
            assert len(gateway.adapters) == 0


class TestGatewayProviderRouting:
    """Tests for provider routing logic."""

    @pytest.mark.asyncio
    async def test_stream_routes_to_openai(self, llm_gateway):
        """Test streaming routes to OpenAI for GPT models."""
        gateway, mock_openai, mock_anthropic = llm_gateway

        # Mock OpenAI streaming
        async def mock_stream(messages, **params):
            yield "Hello"
            yield " from OpenAI"

        mock_openai.stream = mock_stream
        mock_openai.transform_messages = MagicMock(return_value=[{"role": "user", "content": "Hi"}])

        # Mock Router
        async def mock_router_stream(adapter, messages, params):
            async for chunk in adapter.stream(messages, **params):
                yield chunk

        gateway.router.stream_with_retry = mock_router_stream

        # Mock get_provider_from_model
        with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="openai"), \
             patch('app.core.services.llm.gateway.transform_params', return_value={"model": "gpt-4o-mini"}):

            chunks = []
            async for chunk in gateway.stream(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)

            assert chunks == ["Hello", " from OpenAI"]
            mock_openai.transform_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_routes_to_anthropic(self, llm_gateway):
        """Test streaming routes to Anthropic for Claude models."""
        gateway, mock_openai, mock_anthropic = llm_gateway

        # Mock Anthropic streaming
        async def mock_stream(messages, **params):
            yield "Hello"
            yield " from Claude"

        mock_anthropic.stream = mock_stream
        mock_anthropic.transform_messages = MagicMock(
            return_value=([{"role": "user", "content": "Hi"}], {})
        )

        # Mock Router
        async def mock_router_stream(adapter, messages, params):
            async for chunk in adapter.stream(messages, **params):
                yield chunk

        gateway.router.stream_with_retry = mock_router_stream

        # Mock get_provider_from_model
        with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="anthropic"), \
             patch('app.core.services.llm.gateway.transform_params', return_value={"model": "claude-sonnet-4"}):

            chunks = []
            async for chunk in gateway.stream(
                messages=[{"role": "user", "content": "Hi"}],
                model="claude-sonnet-4"
            ):
                chunks.append(chunk)

            assert chunks == ["Hello", " from Claude"]


class TestGatewayModelListing:
    """Tests for model listing."""

    @pytest.mark.asyncio
    async def test_list_models_all_providers(self, llm_gateway):
        """Test listing models from all providers."""
        gateway, mock_openai, mock_anthropic = llm_gateway

        # Mock model responses
        mock_openai.list_models = AsyncMock(return_value=[
            {"id": "gpt-4o", "provider": "OpenAI"}
        ])
        mock_anthropic.list_models = AsyncMock(return_value=[
            {"id": "claude-sonnet-4", "provider": "Anthropic"}
        ])

        results = await gateway.list_models()

        assert "openai" in results
        assert "anthropic" in results
        assert len(results["openai"]) == 1
        assert len(results["anthropic"]) == 1
        assert results["openai"][0]["id"] == "gpt-4o"
        assert results["anthropic"][0]["id"] == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_list_models_specific_provider(self, llm_gateway):
        """Test listing models for specific provider."""
        gateway, mock_openai, mock_anthropic = llm_gateway

        mock_openai.list_models = AsyncMock(return_value=[
            {"id": "gpt-4o", "provider": "OpenAI"}
        ])

        results = await gateway.list_models(provider="openai")

        assert "openai" in results
        assert "anthropic" not in results
        assert len(results["openai"]) == 1

    @pytest.mark.asyncio
    async def test_list_models_handles_provider_error(self, llm_gateway):
        """Test listing models handles errors gracefully."""
        gateway, mock_openai, mock_anthropic = llm_gateway

        # OpenAI fails
        mock_openai.list_models = AsyncMock(side_effect=Exception("API error"))
        # Anthropic succeeds
        mock_anthropic.list_models = AsyncMock(return_value=[
            {"id": "claude-sonnet-4", "provider": "Anthropic"}
        ])

        results = await gateway.list_models()

        # Should return empty list for failed provider
        assert results["openai"] == []
        assert len(results["anthropic"]) == 1


class TestGatewaySystemPromptEnrichment:
    """Tests for system prompt enrichment."""

    def test_enrich_system_prompt_with_tools(self, llm_gateway):
        """Test system prompt enriched with tool instructions."""
        gateway, _, _ = llm_gateway

        base_prompt = "You are a helpful assistant"
        enriched = gateway._enrich_system_prompt(base_prompt, has_tools=True)

        assert "You are a helpful assistant" in enriched
        assert "TOOL ERROR HANDLING" in enriched
        assert "Missing Parameter Errors" in enriched

    def test_enrich_system_prompt_without_tools(self, llm_gateway):
        """Test system prompt not enriched without tools."""
        gateway, _, _ = llm_gateway

        base_prompt = "You are a helpful assistant"
        enriched = gateway._enrich_system_prompt(base_prompt, has_tools=False)

        assert enriched == base_prompt
        assert "TOOL ERROR HANDLING" not in enriched

    def test_enrich_system_prompt_default(self, llm_gateway):
        """Test default system prompt when none provided."""
        gateway, _, _ = llm_gateway

        enriched = gateway._enrich_system_prompt(None, has_tools=False)

        assert "helpful AI assistant" in enriched


class TestGatewayParameterTransformation:
    """Tests for parameter transformation."""

    @pytest.mark.asyncio
    async def test_stream_applies_default_parameters(self, llm_gateway):
        """Test streaming applies provider-specific parameter transformation."""
        gateway, mock_openai, _ = llm_gateway

        async def mock_stream(messages, **params):
            # Verify params were transformed
            assert "model" in params
            yield "Test"

        mock_openai.stream = mock_stream
        mock_openai.transform_messages = MagicMock(return_value=[{"role": "user", "content": "Hi"}])

        # Mock Router
        async def mock_router_stream(adapter, messages, params):
            async for chunk in adapter.stream(messages, **params):
                yield chunk

        gateway.router.stream_with_retry = mock_router_stream

        with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="openai"), \
             patch('app.core.services.llm.gateway.transform_params') as mock_transform:

            mock_transform.return_value = {"model": "gpt-4o-mini", "temperature": 0.7}

            chunks = []
            async for chunk in gateway.stream(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini",
                temperature=0.7
            ):
                chunks.append(chunk)

            # Verify transform_params was called
            mock_transform.assert_called_once_with("openai", {"model": "gpt-4o-mini", "temperature": 0.7})


class TestGatewayUnifiedResponse:
    """Tests for unified response format."""

    @pytest.mark.asyncio
    async def test_stream_returns_text_chunks(self, llm_gateway):
        """Test streaming returns consistent text chunk format."""
        gateway, mock_openai, _ = llm_gateway

        async def mock_stream(messages, **params):
            yield "Chunk1"
            yield "Chunk2"

        mock_openai.stream = mock_stream
        mock_openai.transform_messages = MagicMock(return_value=[{"role": "user", "content": "Hi"}])

        async def mock_router_stream(adapter, messages, params):
            async for chunk in adapter.stream(messages, **params):
                yield chunk

        gateway.router.stream_with_retry = mock_router_stream

        with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="openai"), \
             patch('app.core.services.llm.gateway.transform_params', return_value={"model": "gpt-4o-mini"}):

            chunks = []
            async for chunk in gateway.stream(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            ):
                chunks.append(chunk)
                # Verify all chunks are strings
                assert isinstance(chunk, str)

            assert len(chunks) == 2


class TestGatewayAdapterSelection:
    """Tests for adapter selection by API key."""

    @pytest.mark.asyncio
    async def test_get_adapter_for_admin_key(self, llm_gateway):
        """Test admin API key uses preinitialized adapters."""
        gateway, mock_openai, _ = llm_gateway

        adapter = await gateway._get_adapter_for_provider("openai", api_key_id="admin")

        assert adapter is mock_openai

    @pytest.mark.asyncio
    async def test_get_adapter_for_none_key(self, llm_gateway):
        """Test None API key uses preinitialized adapters."""
        gateway, mock_openai, _ = llm_gateway

        adapter = await gateway._get_adapter_for_provider("openai", api_key_id=None)

        assert adapter is mock_openai

    @pytest.mark.asyncio
    async def test_get_adapter_for_missing_provider(self, llm_gateway):
        """Test missing provider raises error."""
        gateway, _, _ = llm_gateway

        # Remove adapter
        del gateway.adapters["openai"]

        with pytest.raises(ValueError, match="Provider 'openai' not configured"):
            await gateway._get_adapter_for_provider("openai", api_key_id="admin")

    @pytest.mark.asyncio
    async def test_get_adapter_for_custom_api_key(self, llm_gateway):
        """Test custom API key creates new adapter from DB."""
        gateway, _, _ = llm_gateway

        # Mock CRUD
        with patch('app.database.crud.get_api_key_decrypted', new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = "custom-key-value"

            with patch('app.core.services.llm.gateway.OpenAIAdapter') as mock_adapter_class:
                mock_adapter_instance = AsyncMock()
                mock_adapter_class.return_value = mock_adapter_instance

                adapter = await gateway._get_adapter_for_provider("openai", api_key_id="custom-key-id")

                # Should create new adapter with DB key
                mock_get_key.assert_called_once_with("custom-key-id")
                mock_adapter_class.assert_called_once_with("custom-key-value")
                assert adapter is mock_adapter_instance

    @pytest.mark.asyncio
    async def test_get_adapter_for_missing_api_key(self, llm_gateway):
        """Test missing API key in DB raises error."""
        gateway, _, _ = llm_gateway

        with patch('app.database.crud.get_api_key_decrypted', new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = None

            with pytest.raises(ValueError, match="API key 'missing-key' not found"):
                await gateway._get_adapter_for_provider("openai", api_key_id="missing-key")


class TestGatewayErrorPropagation:
    """Tests for error propagation from adapters."""

    @pytest.mark.asyncio
    async def test_stream_propagates_adapter_error(self, llm_gateway):
        """Test streaming propagates adapter errors."""
        gateway, mock_openai, _ = llm_gateway

        async def failing_stream(messages, **params):
            raise Exception("Adapter error")
            yield  # Make it a generator

        mock_openai.stream = failing_stream
        mock_openai.transform_messages = MagicMock(return_value=[{"role": "user", "content": "Hi"}])

        async def mock_router_stream(adapter, messages, params):
            async for chunk in adapter.stream(messages, **params):
                yield chunk

        gateway.router.stream_with_retry = mock_router_stream

        with patch('app.core.services.llm.gateway.get_provider_from_model', return_value="openai"), \
             patch('app.core.services.llm.gateway.transform_params', return_value={"model": "gpt-4o-mini"}):

            with pytest.raises(Exception, match="Adapter error"):
                async for chunk in gateway.stream(
                    messages=[{"role": "user", "content": "Hi"}],
                    model="gpt-4o-mini"
                ):
                    pass
