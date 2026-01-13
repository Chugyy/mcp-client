#!/usr/bin/env python3
# app/api/v1/schemas/resources.py
"""
Pydantic schemas for RAG resources.
Compliant with MCP pattern (ARCHITECTURE_VALIDATION.md).
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from app.api.v1.schemas.base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema

if TYPE_CHECKING:
    from .uploads import UploadResponse


class ResourceCreate(BaseCreateSchema):
    """Schema for creating a RAG resource."""

    embedding_model: str = Field(
        default='text-embedding-3-large',
        description="OpenAI embedding model"
    )
    embedding_dim: int = Field(
        default=3072,
        ge=1,
        le=4096,
        description="Embedding vector dimension"
    )

    @validator('embedding_model')
    def validate_embedding_model(cls, v):
        """Validates that the model is in the allowed list."""
        allowed_models = [
            'text-embedding-3-small',
            'text-embedding-3-large',
            'text-embedding-ada-002'
        ]
        if v not in allowed_models:
            raise ValueError(
                f"Invalid embedding model '{v}'. "
                f"Allowed: {', '.join(allowed_models)}"
            )
        return v

    @validator('embedding_dim')
    def validate_embedding_dim(cls, v, values):
        """Validates that the dimension matches the model."""
        model = values.get('embedding_model')

        # Expected dimensions by model
        expected_dims = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536
        }

        if model and model in expected_dims:
            expected = expected_dims[model]
            if v != expected:
                raise ValueError(
                    f"Model '{model}' expects dimension {expected}, got {v}"
                )

        return v


class ResourceUpdate(BaseUpdateSchema):
    """Schema for updating a resource."""
    pass


class ResourceResponse(BaseResponseSchema):
    """Response schema for a resource."""

    name: str
    description: Optional[str]
    enabled: bool
    status: str
    chunk_count: int
    embedding_model: str
    embedding_dim: int
    indexed_at: Optional[datetime]
    error_message: Optional[str]
    is_system: bool = False

    class Config:
        from_attributes = True


class ResourceWithUploadsResponse(ResourceResponse):
    """Resource response with uploads list."""

    uploads: List['UploadResponse']

    class Config:
        from_attributes = True
