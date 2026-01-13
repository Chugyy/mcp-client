#!/usr/bin/env python3
# app/api/v1/schemas/services.py
"""LLM service schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ServiceCreate(BaseModel):
    """Create LLM service request."""
    name: str = Field(..., min_length=1)
    provider: str = Field(..., pattern='^(openai|anthropic|mcp|resource|custom)$')
    description: Optional[str] = None
    status: str = Field(default='active', pattern='^(active|inactive|deprecated)$')


class ServiceUpdate(BaseModel):
    """Update LLM service request."""
    name: Optional[str] = None
    provider: Optional[str] = Field(None, pattern='^(openai|anthropic|mcp|resource|custom)$')
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern='^(active|inactive|deprecated)$')


class ServiceResponse(BaseModel):
    """LLM service response."""
    id: str
    name: str
    provider: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
