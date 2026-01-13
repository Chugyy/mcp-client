#!/usr/bin/env python3
# app/api/v1/schemas/user_providers.py
"""User provider schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserProviderCreate(BaseModel):
    """Create user provider request."""
    service_id: str = Field(..., min_length=1)
    api_key_id: Optional[str] = None
    enabled: bool = True


class UserProviderUpdate(BaseModel):
    """Update user provider request."""
    api_key_id: Optional[str] = None
    enabled: Optional[bool] = None


class UserProviderResponse(BaseModel):
    """User provider response."""
    id: str
    user_id: str
    service_id: str
    api_key_id: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
