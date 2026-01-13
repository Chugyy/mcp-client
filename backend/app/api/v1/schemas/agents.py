#!/usr/bin/env python3
# app/api/v1/schemas/agents.py
"""Pydantic schemas for agents."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from app.api.v1.schemas.base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema
from datetime import datetime


class AgentCreate(BaseCreateSchema):
    """Schema for agent creation."""

    system_prompt: str = Field(..., min_length=1, max_length=10000, description="Agent system prompt")
    tags: List[str] = Field(default=[], description="Agent tags (max 50)")
    mcp_configs: List[Dict[str, Any]] = Field(default=[], description="MCP configurations (max 20)")
    resources: List[Dict[str, Any]] = Field(default=[], description="Resources (max 20)")

    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """Validates that system_prompt is not empty after trim."""
        if not v or not v.strip():
            raise ValueError('system_prompt cannot be empty')

        v = v.strip()

        if len(v) > 10000:
            raise ValueError('system_prompt too long (max 10000 characters)')

        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validates and normalizes tags."""
        if not v:
            return []

        if len(v) > 50:
            raise ValueError('Too many tags (max 50)')

        # Normalization: lowercase, trim, deduplication
        normalized = []
        for tag in v:
            if not isinstance(tag, str):
                continue

            cleaned = tag.strip().lower()

            if not cleaned:
                continue

            if len(cleaned) > 50:
                raise ValueError(f'Tag too long: "{cleaned}" (max 50 characters)')

            if cleaned not in normalized:
                normalized.append(cleaned)

        return normalized

    @validator('mcp_configs')
    def validate_mcp_configs(cls, v):
        """Validates MCP configurations."""
        if not v:
            return []

        if len(v) > 20:
            raise ValueError('Too many MCP configurations (max 20)')

        for config in v:
            if not isinstance(config, dict):
                raise ValueError('Each MCP config must be a dict')

            if 'server_id' not in config:
                raise ValueError('MCP config must have server_id')

        return v

    @validator('resources')
    def validate_resources(cls, v):
        """Validates resources."""
        if not v:
            return []

        if len(v) > 20:
            raise ValueError('Too many resources (max 20)')

        for resource in v:
            if not isinstance(resource, dict):
                raise ValueError('Each resource must be a dict')

            if 'id' not in resource:
                raise ValueError('Resource must have id')

        return v


class AgentUpdate(BaseUpdateSchema):
    """Schema for agent update."""

    system_prompt: Optional[str] = Field(None, min_length=1, max_length=10000)
    tags: Optional[List[str]] = None
    mcp_configs: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None

    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """Validates that system_prompt is not empty after trim."""
        if v is None:
            return v

        if not v.strip():
            raise ValueError('system_prompt cannot be empty')

        return v.strip()

    @validator('tags')
    def validate_tags(cls, v):
        """Validates and normalizes tags."""
        if v is None:
            return v

        if len(v) > 50:
            raise ValueError('Too many tags (max 50)')

        normalized = []
        for tag in v:
            if not isinstance(tag, str):
                continue

            cleaned = tag.strip().lower()

            if not cleaned:
                continue

            if len(cleaned) > 50:
                raise ValueError(f'Tag too long: "{cleaned}" (max 50 characters)')

            if cleaned not in normalized:
                normalized.append(cleaned)

        return normalized


class AgentResponse(BaseResponseSchema):
    """Schema for agent API response."""

    user_id: str
    name: str
    description: Optional[str]
    system_prompt: str
    tags: List[str]
    enabled: bool
    is_system: bool = False
    avatar_url: Optional[str] = None
    mcp_configs: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
