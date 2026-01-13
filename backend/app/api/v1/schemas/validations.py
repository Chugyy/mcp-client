#!/usr/bin/env python3
# app/api/v1/schemas/validations.py
"""
Pydantic schemas for validations.

Inherits from BaseResponseSchema but does NOT use name/description/enabled fields
from BaseCreateSchema because Validation uses specific fields (title, source, process).
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from .base import BaseResponseSchema


class ValidationCreate(BaseModel):
    """
    Schema for creating a validation.

    Note: Does NOT inherit from BaseCreateSchema because fields are different:
    - title instead of name
    - source, process instead of enabled

    Strict validation according to MCP standards:
    - title: 1-100 chars, pattern ^[a-zA-Z0-9\s\-_\.]+$
    - description: max 500 chars (optional)
    - source: enum (tool_call | manual | automation)
    - process: enum (llm_stream | workflow | manual)
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Validation title (1-100 characters)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description (max 500 characters)"
    )
    source: Literal['tool_call', 'manual', 'automation'] = Field(
        ...,
        description="Validation source"
    )
    process: Literal['llm_stream', 'workflow', 'manual'] = Field(
        ...,
        description="Validation process"
    )
    agent_id: Optional[str] = Field(
        None,
        description="Associated agent ID (optional)"
    )

    @validator('title')
    def validate_title_pattern(cls, v):
        """Validates pattern: ^[a-zA-Z0-9\s\-_\.]+$"""
        import re

        if not v or not v.strip():
            raise ValueError('title cannot be empty')

        v = v.strip()

        # Pattern: letters, digits, spaces, hyphens, underscores, dots
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError(
                'title contains invalid characters. '
                'Allowed: letters, numbers, spaces, hyphens, underscores, dots'
            )

        return v

    @validator('description')
    def clean_description(cls, v):
        """Cleans the description (trim, None if empty)."""
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class ValidationUpdate(BaseModel):
    """
    Schema for updating a validation's status.

    Only the status can be modified directly via PATCH.
    Transitions must respect ALLOWED_TRANSITIONS.
    """

    status: Literal['pending', 'approved', 'rejected', 'feedback', 'cancelled'] = Field(
        ...,
        description="New validation status"
    )


class ValidationResponse(BaseResponseSchema):
    """
    Schema for API responses GET /validations.

    Includes all validation fields + timestamps (inherited from BaseResponseSchema).
    """

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

    class Config:
        from_attributes = True


class ApproveValidationRequest(BaseModel):
    """
    Request to approve a validation.

    If always_allow=True, the tool will be automatically approved for future calls.
    """

    always_allow: bool = Field(
        False,
        description="Auto-approve this tool for future calls"
    )


class RejectValidationRequest(BaseModel):
    """
    Request to reject a validation.

    Reason is optional but recommended for traceability.
    """

    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Rejection reason (optional, max 500 characters)"
    )

    @validator('reason')
    def clean_reason(cls, v):
        """Cleans the reason (trim, None if empty)."""
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class FeedbackValidationRequest(BaseModel):
    """
    Request to provide feedback on a validation.

    The feedback will be transmitted to the LLM which will decide the action to take
    (re-call with modified args, cancellation, request clarifications, etc.).
    """

    feedback: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User feedback (1-500 characters)"
    )

    @validator('feedback')
    def validate_feedback_not_empty(cls, v):
        """Validates that feedback is not empty after trim."""
        if not v or not v.strip():
            raise ValueError('feedback cannot be empty')
        return v.strip()
