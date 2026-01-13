#!/usr/bin/env python3
# app/api/v1/schemas/users.py
"""User schemas."""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class UserUpdate(BaseModel):
    """User profile update request."""
    name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    name: str
    preferences: Dict[str, Any]
    permission_level: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
