#!/usr/bin/env python3
# app/api/v1/schemas/validations_api.py
"""Validation request schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ValidationCreate(BaseModel):
    """Create validation request."""
    agent_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    source: str
    process: str


class ValidationUpdate(BaseModel):
    """Update validation request."""
    status: str = Field(..., pattern='^(pending|validated|cancelled|feedback)$')


class ValidationResponse(BaseModel):
    """Validation response."""
    id: str
    user_id: str
    agent_id: Optional[str] = None
    chat_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    source: str
    process: str
    status: str
    # Tool call fields
    tool_name: Optional[str] = None
    server_id: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[dict] = None
    # Execution linking
    execution_id: Optional[str] = None
    # Expiration tracking
    expires_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
