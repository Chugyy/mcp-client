#!/usr/bin/env python3
# app/api/v1/schemas/auth.py
"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Access token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    name: str = Field(..., min_length=1, description="Full name")


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str
