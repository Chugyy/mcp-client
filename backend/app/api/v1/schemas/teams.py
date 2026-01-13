#!/usr/bin/env python3
# app/api/v1/schemas/teams.py
"""Team schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TeamCreate(BaseModel):
    """Create new team request."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    tags: List[str] = []
    enabled: bool = True


class TeamUpdate(BaseModel):
    """Update team request."""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


class TeamResponse(BaseModel):
    """Team response."""
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    tags: List[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MembershipCreate(BaseModel):
    """Create team membership request."""
    agent_id: str
    enabled: bool = True


class MembershipResponse(BaseModel):
    """Team membership response."""
    id: str
    team_id: str
    agent_id: str
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True
