#!/usr/bin/env python3
# app/core/schemas/errors.py
"""
Standardized error schemas for API responses (RFC 7807 inspired).

Used by exception handlers to return structured error messages.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any


class ErrorDetail(BaseModel):
    """
    Represents a single validation error for a specific field.

    Attributes:
        field: Field path where error occurred (e.g., "name", "config → url")
        message: Descriptive error message
        value: The value that failed validation (optional)
    """

    field: str = Field(..., description="Field path in error")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="Invalid value provided")


class ProblemDetails(BaseModel):
    """
    RFC 7807-inspired standardized error response format.

    Attributes:
        type: Machine-readable error type (e.g., "ValidationError")
        title: Short human-readable title (e.g., "Validation Failed")
        status: HTTP status code (400, 404, 422, etc.)
        detail: Detailed explanation of the error
        instance: URI of the request that caused the error (optional)
        errors: List of validation errors for 422 responses (optional)
        timestamp: ISO 8601 timestamp when error occurred (optional)
        trace_id: Unique ID for error tracing (optional, Phase 2)
    """

    type: str = Field(..., description="Machine-readable error type")
    title: str = Field(..., description="Human-readable error title")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Detailed error explanation")
    instance: Optional[str] = Field(None, description="Request URI that caused error")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Validation errors list")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")
    trace_id: Optional[str] = Field(None, description="Unique trace ID for debugging")

    class Config:
        # Exclude None values from serialization
        json_encoders = {type(None): lambda v: None}
