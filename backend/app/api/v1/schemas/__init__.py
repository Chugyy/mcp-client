#!/usr/bin/env python3
# app/api/v1/schemas/__init__.py
"""
Pydantic schemas for API v1.

All schemas are organized by domain for better maintainability.
Import from this module for convenience:

    from app.api.v1.schemas import AgentCreate, UserResponse

Or import directly from domain modules:

    from app.api.v1.schemas.agents import AgentCreate
"""

# Base schemas
from .base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema

# Auth
from .auth import Token, UserRegister, UserLogin

# Users
from .users import UserUpdate, UserResponse

# Agents
from .agents import AgentCreate, AgentUpdate, AgentResponse

# Teams
from .teams import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    MembershipCreate,
    MembershipResponse,
)

# Chats
from .chats import (
    ChatCreate,
    ChatResponse,
    MessageCreate,
    MessageResponse,
    MessageStreamRequest,
    ChatRequest,
)

# MCP Servers
from .servers import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ConfigurationCreate,
    ConfigurationResponse,
)

# LLM Models
from .models import ModelCreate, ModelUpdate, ModelResponse

# LLM Services
from .services import ServiceCreate, ServiceUpdate, ServiceResponse

# API Keys
from .api_keys import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyResponseWithValue,
)

# User Providers
from .user_providers import (
    UserProviderCreate,
    UserProviderUpdate,
    UserProviderResponse,
)

# Resources
from .resources import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceWithUploadsResponse,
)

# Automation
from .automation import AutomationCreate, AutomationUpdate

# Uploads
from .uploads import UploadResponse

# Validations
from .validations_api import (
    ValidationCreate,
    ValidationUpdate,
    ValidationResponse,
)

__all__ = [
    # Base
    "BaseCreateSchema",
    "BaseUpdateSchema",
    "BaseResponseSchema",
    # Auth
    "Token",
    "UserRegister",
    "UserLogin",
    # Users
    "UserUpdate",
    "UserResponse",
    # Agents
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    # Teams
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "MembershipCreate",
    "MembershipResponse",
    # Chats
    "ChatCreate",
    "ChatResponse",
    "MessageCreate",
    "MessageResponse",
    "MessageStreamRequest",
    "ChatRequest",
    # MCP Servers
    "ServerCreate",
    "ServerUpdate",
    "ServerResponse",
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ConfigurationCreate",
    "ConfigurationResponse",
    # LLM Models
    "ModelCreate",
    "ModelUpdate",
    "ModelResponse",
    # LLM Services
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    # API Keys
    "ApiKeyCreate",
    "ApiKeyUpdate",
    "ApiKeyResponse",
    "ApiKeyResponseWithValue",
    # User Providers
    "UserProviderCreate",
    "UserProviderUpdate",
    "UserProviderResponse",
    # Resources
    "ResourceCreate",
    "ResourceUpdate",
    "ResourceResponse",
    "ResourceWithUploadsResponse",
    # Automation
    "AutomationCreate",
    "AutomationUpdate",
    # Uploads
    "UploadResponse",
    # Validations
    "ValidationCreate",
    "ValidationUpdate",
    "ValidationResponse",
]
