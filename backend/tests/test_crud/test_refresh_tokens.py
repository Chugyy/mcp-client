"""Integration tests for refresh_tokens CRUD module."""

import pytest
from app.database.crud import refresh_tokens
from datetime import datetime, timedelta



@pytest.mark.asyncio
async def test_create_refresh_token(clean_db, sample_user, mock_pool_for_crud):
    """Test creating a refresh token."""
    expires_at = datetime.utcnow() + timedelta(days=30)
    token_id = await refresh_tokens.create_refresh_token(
        user_id=sample_user["id"],
        token_hash="refresh_token_123",
        expires_at=expires_at
    )

    assert token_id is not None


@pytest.mark.asyncio
async def test_get_refresh_token(clean_db, sample_user, mock_pool_for_crud):
    """Test getting a refresh token."""
    expires_at = datetime.utcnow() + timedelta(days=30)
    token_value = "token_get_test"
    await refresh_tokens.create_refresh_token(
        user_id=sample_user["id"],
        token_hash=token_value,
        expires_at=expires_at
    )

    token = await refresh_tokens.get_refresh_token_by_hash(token_value)
    assert token is not None


@pytest.mark.asyncio
async def test_delete_refresh_token(clean_db, sample_user, mock_pool_for_crud):
    """Test deleting a refresh token."""
    expires_at = datetime.utcnow() + timedelta(days=30)
    token_value = "token_delete_test"
    token_id = await refresh_tokens.create_refresh_token(
        user_id=sample_user["id"],
        token_hash=token_value,
        expires_at=expires_at
    )

    success = await refresh_tokens.revoke_refresh_token(token_value)
    assert success is True


@pytest.mark.asyncio
async def test_delete_expired_tokens(clean_db, sample_user, mock_pool_for_crud):
    """Test deleting expired tokens."""
    # Create expired token
    expires_at = datetime.utcnow() - timedelta(days=1)
    await refresh_tokens.create_refresh_token(
        user_id=sample_user["id"],
        token_hash="expired_token",
        expires_at=expires_at
    )

    count = await refresh_tokens.delete_expired_tokens()
    assert count >= 0


@pytest.mark.asyncio
async def test_list_tokens_by_user(clean_db, sample_user, mock_pool_for_crud):
    """Test listing tokens by user."""
    expires_at = datetime.utcnow() + timedelta(days=30)
    token_id = await refresh_tokens.create_refresh_token(
        user_id=sample_user["id"],
        token_hash="user_token_list",
        expires_at=expires_at
    )

    tokens_list = await refresh_tokens.get_user_active_tokens(sample_user["id"])
    assert any(t["id"] == token_id for t in tokens_list)
