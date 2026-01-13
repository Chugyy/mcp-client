#!/usr/bin/env python3
# app/api/v1/schemas/chats.py
"""Chat and message schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class ChatCreate(BaseModel):
    """Create new chat session request."""
    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    title: str = Field(..., min_length=1)

    @validator('team_id')
    def validate_agent_or_team(cls, v, values):
        """Validate that agent_id and team_id are not both set."""
        # Allow empty chats (lazy initialization)
        # Only validate that agent_id and team_id are not both set
        if v and values.get('agent_id'):
            raise ValueError('Cannot specify both agent_id and team_id')
        return v


class ChatResponse(BaseModel):
    """Chat session response."""
    id: str
    user_id: str
    agent_id: Optional[str]
    team_id: Optional[str]
    title: str
    model: Optional[str] = None
    initialized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Create new message request."""
    role: str = Field(..., pattern='^(user|assistant)$')
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = {}


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    chat_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    turn_id: Optional[str] = None
    sequence_index: Optional[int] = None

    class Config:
        from_attributes = True


class MessageStreamRequest(BaseModel):
    """
    Request for streaming a message in an existing chat.

    Used by POST /chats/{chat_id}/stream endpoint.
    Simpler than ChatRequest since chat_id is in the URL.
    """
    message: str = Field(..., min_length=1, description="Message content to send")
    model: Optional[str] = Field(None, description="LLM model to use (e.g., gpt-4o-mini, claude-sonnet-4-5)")
    api_key_id: Optional[str] = Field(default="admin", description="API key ID to use")
    agent_id: Optional[str] = Field(None, description="Required for first message in empty chat")


class ChatRequest(BaseModel):
    """Chat request for streaming."""
    message: str = Field(..., min_length=1)
    agent_id: Optional[str] = None
    chat_id: Optional[str] = None
    model: Optional[str] = None
    api_key_id: Optional[str] = "admin"
    top_k: int = 5
