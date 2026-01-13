#!/usr/bin/env python3
# app/api/v1/schemas/servers.py
"""
Pydantic schemas for MCP servers.

Inherits from BaseCreateSchema/BaseUpdateSchema/BaseResponseSchema to ensure
consistent validation with the rest of the application.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Literal
from datetime import datetime
from .base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema


class ServerCreate(BaseCreateSchema):
    """
    Schema for creating an MCP server.

    Strict validation according to ARCHITECTURE_VALIDATION.md:
    - name: 1-100 chars, pattern alphanum + spaces + - _ .
    - description: max 500 chars
    - type: http | npx | uvx | docker
    - url: max 2048 chars (required if type=http)
    - args: max 50 items (required if type stdio)
    - env: max 100 vars, keys pattern ^[A-Z][A-Z0-9_]*$, values max 1000 chars
    """

    type: Literal['http', 'npx', 'uvx', 'docker'] = Field(
        ...,
        description="MCP server type"
    )

    # ===== HTTP FIELDS =====
    url: Optional[str] = Field(
        None,
        max_length=2048,
        description="MCP server URL (required if type=http)"
    )
    auth_type: Optional[Literal['api-key', 'oauth', 'none']] = Field(
        None,
        description="Authentication type (for type=http)"
    )
    service_id: Optional[str] = Field(
        None,
        description="Associated service ID (for type=http + api-key)"
    )
    api_key_value: Optional[str] = Field(
        None,
        description="API key value (for type=http + auth_type=api-key)"
    )

    # ===== STDIO FIELDS (npx, uvx, docker) =====
    args: Optional[List[str]] = Field(
        None,
        max_items=50,
        description="Arguments for stdio servers (max 50 items)"
    )
    env: Optional[Dict[str, str]] = Field(
        None,
        description="Environment variables (max 100 vars)"
    )

    @validator('url')
    def validate_http_url(cls, v, values):
        """Validates that url is provided and valid if type=http."""
        server_type = values.get('type')

        if server_type == 'http':
            if not v:
                raise ValueError('url is required for HTTP servers')

            # Basic URL format validation
            if not v.startswith(('http://', 'https://')):
                raise ValueError('url must start with http:// or https://')

        return v

    @validator('args')
    def validate_stdio_args(cls, v, values):
        """Validates that args is provided and valid if type stdio."""
        server_type = values.get('type')

        if server_type in ['npx', 'uvx', 'docker']:
            if not v or len(v) == 0:
                raise ValueError(f'args is required for {server_type} servers')

            # Validate length of each arg (max 500 chars)
            for arg in v:
                if len(arg) > 500:
                    raise ValueError(f'Each arg must be max 500 characters')

        return v

    @validator('env')
    def validate_env_format(cls, v):
        """
        Validates environment variable format.

        - Max 100 variables
        - Keys: pattern ^[A-Z][A-Z0-9_]*$ (e.g. GITHUB_TOKEN)
        - Values: max 1000 chars
        """
        if v is None:
            return v

        if len(v) > 100:
            raise ValueError('Maximum 100 environment variables allowed')

        import re
        env_key_pattern = r'^[A-Z][A-Z0-9_]*$'

        for key, value in v.items():
            # Validate key
            if not re.match(env_key_pattern, key):
                raise ValueError(
                    f'Invalid environment variable key \'{key}\'. '
                    f'Must start with uppercase letter and contain only uppercase letters, digits, and underscores. '
                    f'Example: GITHUB_TOKEN, API_KEY'
                )

            # Validate key length
            if len(key) > 100:
                raise ValueError(f'Environment variable key \'{key}\' too long (max 100 characters)')

            # Validate value length
            if len(value) > 1000:
                raise ValueError(f'Environment variable value for \'{key}\' too long (max 1000 characters)')

        return v


class ServerUpdate(BaseUpdateSchema):
    """
    Schema for updating an MCP server.

    Modifiable fields:
    - name, description, enabled (inherited)
    - url, auth_type, service_id (HTTP only)

    Note: type, args, env are NOT modifiable after creation
    """

    url: Optional[str] = Field(None, max_length=2048)
    auth_type: Optional[Literal['api-key', 'oauth', 'none']] = None
    service_id: Optional[str] = None

    @validator('url')
    def validate_url_format(cls, v):
        """Validates the URL format if provided."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('url must start with http:// or https://')
        return v


class ServerResponse(BaseResponseSchema):
    """
    Schema for API responses GET /servers.

    Includes all server fields + timestamps.
    Note: env is NEVER returned for security reasons.
    """

    name: str
    description: Optional[str]
    type: str

    # HTTP fields
    url: Optional[str] = None
    auth_type: Optional[str] = None
    service_id: Optional[str] = None
    api_key_id: Optional[str] = None

    # Stdio fields (npx, uvx, docker)
    args: Optional[List[str]] = None
    # env: NEVER returned (security)

    enabled: bool
    status: str
    status_message: Optional[str] = None
    last_health_check: Optional[datetime] = None
    is_system: bool = False

    # Optional fields (if with_tools=true)
    tools: Optional[List[Dict]] = None
    stale: Optional[bool] = None

    class Config:
        from_attributes = True


# ===== MCP TOOL SCHEMAS =====


class ToolCreate(BaseModel):
    """Create MCP tool request."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    enabled: bool = True


class ToolUpdate(BaseModel):
    """Update MCP tool request."""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ToolResponse(BaseModel):
    """MCP tool response."""
    id: str
    server_id: str
    name: str
    description: Optional[str]
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ===== MCP CONFIGURATION SCHEMAS =====


class ConfigurationCreate(BaseModel):
    """Create MCP configuration request."""
    entity_type: str = Field(..., pattern='^(server|resource)$')
    entity_id: str
    config_data: dict = {}
    enabled: bool = True


class ConfigurationResponse(BaseModel):
    """MCP configuration response."""
    id: str
    agent_id: str
    entity_type: str
    entity_id: str
    config_data: dict
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True
