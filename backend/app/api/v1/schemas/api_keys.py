#!/usr/bin/env python3
# app/api/v1/schemas/api_keys.py
"""API key schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApiKeyCreate(BaseModel):
    """Create API key request."""
    plain_value: str = Field(..., min_length=1)
    service_id: str = Field(..., min_length=1)


class ApiKeyUpdate(BaseModel):
    """Update API key request."""
    plain_value: str = Field(..., min_length=1)


class ApiKeyResponse(BaseModel):
    """API key response (without plain value)."""
    id: str
    service_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiKeyResponseWithValue(BaseModel):
    """API key response with decrypted value."""
    id: str
    plain_value: str
    service_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
