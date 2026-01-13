#!/usr/bin/env python3
# app/api/v1/schemas/uploads.py
"""Upload schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UploadResponse(BaseModel):
    """Upload response."""
    id: str
    user_id: Optional[str]
    agent_id: Optional[str]
    resource_id: Optional[str]
    type: str
    filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
