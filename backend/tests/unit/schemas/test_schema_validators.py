#!/usr/bin/env python3
"""
Unit tests for Pydantic schema validators.

Tests validator logic in isolation without requiring database or API context.
Focus areas:
- Tag normalization (AgentCreate)
- System prompt validation (AgentCreate)
- Name pattern validation (BaseCreateSchema)
- Environment variable validation (ServerCreate)
- Embedding model/dimension validation (ResourceCreate)
- Title pattern validation (ValidationCreate)
"""

import pytest
from pydantic import ValidationError
from app.api.v1.schemas.agents import AgentCreate, AgentUpdate
from app.api.v1.schemas.base import BaseCreateSchema
from app.api.v1.schemas.servers import ServerCreate
from app.api.v1.schemas.resources import ResourceCreate
from app.api.v1.schemas.validations import ValidationCreate


# ===== AGENT VALIDATORS =====

class TestAgentTagsValidation:
    """Test tag normalization and validation in AgentCreate."""

    def test_tags_normalization_lowercase(self):
        """Test that tags are converted to lowercase."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt",
            tags=["PYTHON", "API", "Test"]
        )
        assert agent.tags == ["python", "api", "test"]

    def test_tags_normalization_trim_whitespace(self):
        """Test that tags are trimmed of leading/trailing whitespace."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt",
            tags=["  python  ", "api ", " test"]
        )
        assert agent.tags == ["python", "api", "test"]

    def test_tags_normalization_deduplication(self):
        """Test that duplicate tags are removed."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt",
            tags=["python", "PYTHON", "  Python  ", "api", "api"]
        )
        assert agent.tags == ["python", "api"]

    def test_tags_normalization_combined(self):
        """Test all normalizations combined: lowercase, trim, dedupe."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt",
            tags=["  PYTHON  ", "python", "API", "api  ", "Test", "test"]
        )
        assert agent.tags == ["python", "api", "test"]

    def test_tags_max_count(self):
        """Test that more than 50 tags are rejected."""
        with pytest.raises(ValidationError, match="Too many tags"):
            AgentCreate(
                name="Test Agent",
                system_prompt="Test prompt",
                tags=[f"tag{i}" for i in range(51)]
            )

    def test_tags_max_length_per_tag(self):
        """Test that tags over 50 chars are rejected."""
        with pytest.raises(ValidationError, match="Tag too long"):
            AgentCreate(
                name="Test Agent",
                system_prompt="Test prompt",
                tags=["a" * 51]
            )

    def test_tags_empty_after_normalization_skipped(self):
        """Test that tags that become empty after trim are skipped (not rejected)."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt",
            tags=["   ", "valid_tag", "  "]
        )
        # Empty tags are silently skipped during normalization
        assert agent.tags == ["valid_tag"]

    def test_tags_optional_empty_list(self):
        """Test that tags field is optional and defaults to empty list."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt"
        )
        assert agent.tags == []


class TestAgentSystemPromptValidation:
    """Test system prompt validation in AgentCreate."""

    def test_system_prompt_required(self):
        """Test that system_prompt is required."""
        with pytest.raises(ValidationError, match="Field required"):
            AgentCreate(
                name="Test Agent"
            )

    def test_system_prompt_min_length(self):
        """Test that system_prompt must be at least 1 character."""
        with pytest.raises(ValidationError, match="at least 1 character"):
            AgentCreate(
                name="Test Agent",
                system_prompt=""
            )

    def test_system_prompt_max_length(self):
        """Test that system_prompt cannot exceed 10,000 characters."""
        with pytest.raises(ValidationError, match="at most 10000 characters"):
            AgentCreate(
                name="Test Agent",
                system_prompt="a" * 10001
            )

    def test_system_prompt_valid(self):
        """Test that valid system prompts are accepted."""
        prompt = "You are a helpful assistant specialized in Python development."
        agent = AgentCreate(
            name="Test Agent",
            system_prompt=prompt
        )
        assert agent.system_prompt == prompt


# ===== BASE SCHEMA VALIDATORS =====

class TestBaseSchemaNameValidation:
    """Test name pattern validation in BaseCreateSchema."""

    def test_name_valid_patterns(self):
        """Test that valid name patterns are accepted."""
        valid_names = [
            "Agent Name",
            "simple-name",
            "name_with_underscores",
            "Name123",
            "Name.With.Dots",
            "Name-With-Everything_123.Test"
        ]

        for name in valid_names:
            agent = AgentCreate(
                name=name,
                system_prompt="Test prompt"
            )
            assert agent.name == name

    def test_name_invalid_special_chars(self):
        """Test that names with invalid special characters are rejected."""
        invalid_names = [
            "Name@Invalid",
            "Name#Invalid",
            "Name$Invalid",
            "Name%Invalid",
            "Name&Invalid",
            "Name*Invalid",
            "Name(Invalid)",
            "Name[Invalid]",
            "Name{Invalid}",
            "Name/Invalid",
            "Name\\Invalid"
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError, match="contains invalid characters"):
                AgentCreate(
                    name=name,
                    system_prompt="Test prompt"
                )

    def test_name_min_length(self):
        """Test that names must be at least 1 character."""
        with pytest.raises(ValidationError):
            AgentCreate(
                name="",
                system_prompt="Test prompt"
            )

    def test_name_max_length(self):
        """Test that names cannot exceed 100 characters."""
        with pytest.raises(ValidationError, match="at most 100 characters"):
            AgentCreate(
                name="a" * 101,
                system_prompt="Test prompt"
            )

    def test_name_whitespace_normalization(self):
        """Test that leading/trailing whitespace is trimmed."""
        agent = AgentCreate(
            name="  Agent Name  ",
            system_prompt="Test prompt"
        )
        assert agent.name == "Agent Name"


# ===== SERVER VALIDATORS =====

class TestServerEnvValidation:
    """Test environment variable validation in ServerCreate."""

    def test_env_valid_format(self):
        """Test that valid env vars are accepted."""
        server = ServerCreate(
            name="Test Server",
            type="npx",
            args=["@modelcontextprotocol/server-test"],
            env={
                "GITHUB_TOKEN": "ghp_test123",
                "API_KEY": "test_key",
                "DB_HOST": "localhost"
            }
        )
        assert "GITHUB_TOKEN" in server.env
        assert server.env["GITHUB_TOKEN"] == "ghp_test123"

    def test_env_invalid_key_lowercase_start(self):
        """Test that env keys starting with lowercase are rejected."""
        with pytest.raises(ValidationError, match="Invalid environment variable key"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["test"],
                env={"githubToken": "test"}
            )

    def test_env_invalid_key_special_chars(self):
        """Test that env keys with invalid characters are rejected."""
        with pytest.raises(ValidationError, match="Invalid environment variable key"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["test"],
                env={"GITHUB-TOKEN": "test"}
            )

    def test_env_max_count(self):
        """Test that more than 100 env vars are rejected."""
        with pytest.raises(ValidationError, match="Maximum 100 environment variables"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["test"],
                env={f"VAR_{i}": "value" for i in range(101)}
            )

    def test_env_key_max_length(self):
        """Test that env keys over 100 chars are rejected."""
        with pytest.raises(ValidationError, match="too long"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["test"],
                env={f"A{'B' * 100}": "value"}
            )

    def test_env_value_max_length(self):
        """Test that env values over 1000 chars are rejected."""
        with pytest.raises(ValidationError, match="too long"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["test"],
                env={"API_KEY": "a" * 1001}
            )

    def test_env_optional(self):
        """Test that env field is optional."""
        server = ServerCreate(
            name="Test Server",
            type="npx",
            args=["test"]
        )
        assert server.env is None


class TestServerArgsValidation:
    """Test args validation for stdio servers."""

    def test_args_required_for_npx(self):
        """Test that args is required for npx servers."""
        with pytest.raises(ValidationError, match="args is required"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=[]  # Empty list should trigger validation
            )

    def test_args_required_for_uvx(self):
        """Test that args is required for uvx servers."""
        with pytest.raises(ValidationError, match="args is required"):
            ServerCreate(
                name="Test Server",
                type="uvx",
                args=[]  # Empty list should trigger validation
            )

    def test_args_required_for_docker(self):
        """Test that args is required for docker servers."""
        with pytest.raises(ValidationError, match="args is required"):
            ServerCreate(
                name="Test Server",
                type="docker",
                args=[]  # Empty list should trigger validation
            )

    def test_args_max_items(self):
        """Test that more than 50 args are rejected."""
        with pytest.raises(ValidationError):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=[f"arg{i}" for i in range(51)]
            )

    def test_args_item_max_length(self):
        """Test that args over 500 chars are rejected."""
        with pytest.raises(ValidationError, match="max 500 characters"):
            ServerCreate(
                name="Test Server",
                type="npx",
                args=["a" * 501]
            )


class TestServerURLValidation:
    """Test URL validation for HTTP servers."""

    def test_url_required_for_http(self):
        """Test that url is required for HTTP servers."""
        with pytest.raises(ValidationError, match="url is required"):
            ServerCreate(
                name="Test Server",
                type="http",
                url=None  # Explicitly None to trigger validator
            )

    def test_url_must_start_with_http(self):
        """Test that url must start with http:// or https://."""
        with pytest.raises(ValidationError, match="must start with http"):
            ServerCreate(
                name="Test Server",
                type="http",
                url="ftp://example.com"
            )

    def test_url_https_valid(self):
        """Test that https:// URLs are accepted."""
        server = ServerCreate(
            name="Test Server",
            type="http",
            url="https://api.example.com"
        )
        assert server.url == "https://api.example.com"

    def test_url_http_valid(self):
        """Test that http:// URLs are accepted."""
        server = ServerCreate(
            name="Test Server",
            type="http",
            url="http://localhost:8080"
        )
        assert server.url == "http://localhost:8080"


# ===== RESOURCE VALIDATORS =====

class TestResourceEmbeddingValidation:
    """Test embedding model and dimension validation in ResourceCreate."""

    def test_embedding_model_valid_small(self):
        """Test that text-embedding-3-small is accepted with correct dim."""
        resource = ResourceCreate(
            name="Test Resource",
            embedding_model="text-embedding-3-small",
            embedding_dim=1536
        )
        assert resource.embedding_model == "text-embedding-3-small"
        assert resource.embedding_dim == 1536

    def test_embedding_model_valid_large(self):
        """Test that text-embedding-3-large is accepted with correct dim."""
        resource = ResourceCreate(
            name="Test Resource",
            embedding_model="text-embedding-3-large",
            embedding_dim=3072
        )
        assert resource.embedding_model == "text-embedding-3-large"
        assert resource.embedding_dim == 3072

    def test_embedding_model_valid_ada(self):
        """Test that text-embedding-ada-002 is accepted with correct dim."""
        resource = ResourceCreate(
            name="Test Resource",
            embedding_model="text-embedding-ada-002",
            embedding_dim=1536
        )
        assert resource.embedding_model == "text-embedding-ada-002"
        assert resource.embedding_dim == 1536

    def test_embedding_model_invalid(self):
        """Test that invalid models are rejected."""
        with pytest.raises(ValidationError, match="Invalid embedding model"):
            ResourceCreate(
                name="Test Resource",
                embedding_model="text-embedding-invalid"
            )

    def test_embedding_dim_mismatch_small(self):
        """Test that wrong dimension for small model is rejected."""
        with pytest.raises(ValidationError, match="expects dimension 1536"):
            ResourceCreate(
                name="Test Resource",
                embedding_model="text-embedding-3-small",
                embedding_dim=3072
            )

    def test_embedding_dim_mismatch_large(self):
        """Test that wrong dimension for large model is rejected."""
        with pytest.raises(ValidationError, match="expects dimension 3072"):
            ResourceCreate(
                name="Test Resource",
                embedding_model="text-embedding-3-large",
                embedding_dim=1536
            )

    def test_embedding_defaults(self):
        """Test that embedding fields have correct defaults."""
        resource = ResourceCreate(
            name="Test Resource"
        )
        assert resource.embedding_model == "text-embedding-3-large"
        assert resource.embedding_dim == 3072


# ===== VALIDATION VALIDATORS =====

class TestValidationTitleValidation:
    """Test title pattern validation in ValidationCreate."""

    def test_title_valid_patterns(self):
        """Test that valid title patterns are accepted."""
        valid_titles = [
            "Validation Title",
            "simple-title",
            "title_with_underscores",
            "Title123",
            "Title.With.Dots",
            "Title-With-Everything_123.Test"
        ]

        for title in valid_titles:
            validation = ValidationCreate(
                title=title,
                source="manual",
                process="manual"
            )
            assert validation.title == title

    def test_title_invalid_special_chars(self):
        """Test that titles with invalid special characters are rejected."""
        invalid_titles = [
            "Title@Invalid",
            "Title#Invalid",
            "Title$Invalid"
        ]

        for title in invalid_titles:
            with pytest.raises(ValidationError, match="invalid characters"):
                ValidationCreate(
                    title=title,
                    source="manual",
                    process="manual"
                )

    def test_title_whitespace_trimmed(self):
        """Test that leading/trailing whitespace is trimmed."""
        validation = ValidationCreate(
            title="  Validation Title  ",
            source="manual",
            process="manual"
        )
        assert validation.title == "Validation Title"

    def test_title_empty_rejected(self):
        """Test that empty titles are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ValidationCreate(
                title="   ",
                source="manual",
                process="manual"
            )

    def test_title_max_length(self):
        """Test that titles over 100 chars are rejected."""
        with pytest.raises(ValidationError, match="at most 100 characters"):
            ValidationCreate(
                title="a" * 101,
                source="manual",
                process="manual"
            )


class TestValidationDescriptionValidation:
    """Test description cleaning in ValidationCreate."""

    def test_description_trimmed(self):
        """Test that description whitespace is trimmed."""
        validation = ValidationCreate(
            title="Test",
            description="  Test description  ",
            source="manual",
            process="manual"
        )
        assert validation.description == "Test description"

    def test_description_empty_becomes_none(self):
        """Test that empty descriptions become None."""
        validation = ValidationCreate(
            title="Test",
            description="   ",
            source="manual",
            process="manual"
        )
        assert validation.description is None

    def test_description_optional(self):
        """Test that description is optional."""
        validation = ValidationCreate(
            title="Test",
            source="manual",
            process="manual"
        )
        assert validation.description is None

    def test_description_max_length(self):
        """Test that descriptions over 500 chars are rejected."""
        with pytest.raises(ValidationError, match="at most 500 characters"):
            ValidationCreate(
                title="Test",
                description="a" * 501,
                source="manual",
                process="manual"
            )
