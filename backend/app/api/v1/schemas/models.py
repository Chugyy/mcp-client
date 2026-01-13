#!/usr/bin/env python3
# app/api/v1/schemas/llm_models.py
"""LLM model schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ModelCreate(BaseModel):
    """Create LLM model request."""
    service_id: str
    model_name: str = Field(..., min_length=1)
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True


class ModelUpdate(BaseModel):
    """Update LLM model request."""
    model_name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ModelResponse(BaseModel):
    """LLM model response."""
    id: str
    service_id: str
    model_name: str
    display_name: Optional[str]
    description: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
