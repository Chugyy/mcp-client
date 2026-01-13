#!/usr/bin/env python3
# app/api/v1/schemas/base.py
"""
Reusable base schemas (Pydantic mixins).

All domains (agents, servers, resources, etc.) inherit from these classes
to ensure consistent validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class BaseCreateSchema(BaseModel):
    """
    Base schema for creation requests.

    Automatically inherits:
    - name: str (1-100 chars, pattern alphanum + - _ . space)
    - description: Optional[str] (max 500 chars)
    - enabled: bool (default True)
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Resource name (1-100 characters, alphanumeric + spaces + - _ .)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description (max 500 characters)"
    )
    enabled: bool = Field(
        True,
        description="Enable/disable the resource"
    )

    @validator('name')
    def validate_name_pattern(cls, v):
        """Validates name pattern (alphanum + spaces + - _ .)."""
        import re
        if not v or not v.strip():
            raise ValueError('name cannot be empty')

        v = v.strip()

        # Pattern: letters, numbers, spaces, hyphens, underscores, dots
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError(
                'name contains invalid characters. '
                'Allowed: letters, numbers, spaces, hyphens, underscores, dots'
            )

        return v

    @validator('description')
    def clean_description(cls, v):
        """Cleans description (trim, None if empty)."""
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class BaseUpdateSchema(BaseModel):
    """
    Base schema for update requests.

    All fields are optional (partial update).
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None

    @validator('name')
    def validate_name_pattern(cls, v):
        """Validates name pattern if provided."""
        if v is None:
            return v

        import re
        v = v.strip()

        if not v:
            raise ValueError('name cannot be empty')

        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError(
                'name contains invalid characters. '
                'Allowed: letters, numbers, spaces, hyphens, underscores, dots'
            )

        return v

    @validator('description')
    def clean_description(cls, v):
        """Cleans description."""
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class BaseResponseSchema(BaseModel):
    """
    Base schema for API responses.

    Automatically includes:
    - id: str
    - created_at: datetime
    - updated_at: datetime
    """

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (formerly orm_mode)
