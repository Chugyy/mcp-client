"""Core authentication tests: JWT token generation/validation + Password hashing.

Consolidated from test_jwt.py and test_password.py.
Focuses on essential security functionality with 70-80% coverage target.
"""

import pytest
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from jose import jwt

# Mock the refresh_tokens module before any imports
sys.modules['app.database.crud.refresh_tokens'] = MagicMock()

from app.core.utils.auth import (
    create_access_token,
    verify_token,
    create_refresh_token,
    verify_refresh_token,
    generate_refresh_token,
    hash_refresh_token,
    hash_password,
    verify_password,
    authenticate_user
)
from app.database.models import User


# ============================================================================
# Test Helper Functions
# ============================================================================

def create_user_dict(**kwargs):
    """Helper to create a complete user dict with required fields."""
    defaults = {
        "id": "user_123",
        "email": "user@example.com",
        "password": "hashed_password",
        "name": "Test User",
        "preferences": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "permission_level": "validation_required",
        "is_system": False
    }
    defaults.update(kwargs)
    return defaults


# ============================================================================
# JWT Token Generation Tests (8 essential tests from test_jwt.py)
# ============================================================================

class TestJWTTokenGeneration:
    """Test JWT access token creation."""

    def test_create_valid_access_token(self):
        """Test JWT generation with valid user data."""
        user_data = {"sub": "user_123", "email": "test@example.com"}
        token = create_access_token(user_data, expires_delta=timedelta(hours=1))

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test JWT generation with custom expiration time."""
        user_data = {"sub": "user_123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(user_data, expires_delta=expires_delta)

        assert token is not None
        # Decode to verify expiration is set (use same secret as conftest)
        payload = jwt.decode(token, "test-jwt-secret-key-min-32-chars-long-12345", algorithms=["HS256"])
        assert "exp" in payload

    def test_create_access_token_default_expiry(self):
        """Test JWT generation uses default 15-minute expiry when not specified."""
        user_data = {"sub": "user_123"}
        before_creation = datetime.utcnow()
        token = create_access_token(user_data)
        after_creation = datetime.utcnow()

        assert token is not None
        # Decode with same secret as conftest
        payload = jwt.decode(token, "test-jwt-secret-key-min-32-chars-long-12345", algorithms=["HS256"])

        # Verify expiration exists and is reasonable (between 14-16 minutes from creation)
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        min_expected = before_creation + timedelta(minutes=14)
        max_expected = after_creation + timedelta(minutes=16)
        assert min_expected <= exp_time <= max_expected, f"Expiration {exp_time} not within expected range"

    def test_create_token_with_extra_claims(self):
        """Test JWT generation preserves extra claims."""
        user_data = {
            "sub": "user_123",
            "email": "test@example.com",
            "role": "admin"
        }
        token = create_access_token(user_data, expires_delta=timedelta(hours=1))

        # Decode with same secret as conftest
        payload = jwt.decode(token, "test-jwt-secret-key-min-32-chars-long-12345", algorithms=["HS256"])

        assert payload["sub"] == "user_123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"


# ============================================================================
# JWT Token Validation Tests (7 essential tests from test_jwt.py)
# ============================================================================

class TestJWTTokenValidation:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Test JWT validation with valid token."""
        user_id = "user_123"
        user_data = {"sub": user_id}
        token = create_access_token(user_data, expires_delta=timedelta(hours=1))

        verified_user_id = verify_token(token)
        assert verified_user_id == user_id

    def test_verify_expired_token(self):
        """Test JWT validation rejects expired token."""
        user_data = {"sub": "user_123"}
        token = create_access_token(user_data, expires_delta=timedelta(seconds=-10))

        result = verify_token(token)
        assert result is None

    def test_verify_malformed_token(self):
        """Test JWT validation rejects malformed token."""
        malformed_token = "invalid.token.format"

        result = verify_token(malformed_token)
        assert result is None

    def test_verify_token_invalid_signature(self):
        """Test JWT validation rejects token with invalid signature."""
        # Create token with one secret
        user_data = {"sub": "user_123"}
        with patch('config.config.settings') as mock_settings:
            mock_settings.jwt_secret_key = "secret_key_1"
            mock_settings.jwt_algorithm = "HS256"
            token = jwt.encode(user_data, "secret_key_1", algorithm="HS256")

        # Try to verify with different secret
        with patch('config.config.settings') as mock_settings:
            mock_settings.jwt_secret_key = "different_secret"
            mock_settings.jwt_algorithm = "HS256"
            result = verify_token(token)
            assert result is None

    def test_verify_token_missing_sub_claim(self):
        """Test JWT validation rejects token without 'sub' claim."""
        # Create token without 'sub' field
        with patch('config.config.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            token = jwt.encode({"email": "test@example.com"}, "test_secret", algorithm="HS256")

        result = verify_token(token)
        assert result is None

    def test_verify_token_empty_string(self):
        """Test JWT validation rejects empty token string."""
        result = verify_token("")
        assert result is None

    def test_token_expiring_at_boundary(self):
        """Test token expiration at exact boundary (1 second before/after)."""
        user_data = {"sub": "user_123"}

        # Token expiring in 1 second
        token_1sec = create_access_token(user_data, expires_delta=timedelta(seconds=1))
        result = verify_token(token_1sec)
        assert result == "user_123"  # Should be valid immediately after creation

        # Token expired 1 second ago
        token_expired = create_access_token(user_data, expires_delta=timedelta(seconds=-1))
        result = verify_token(token_expired)
        assert result is None  # Should be invalid


# ============================================================================
# Refresh Token Tests (5 essential tests from test_jwt.py)
# ============================================================================

class TestRefreshToken:
    """Test refresh token generation and validation."""

    def test_generate_refresh_token(self):
        """Test refresh token generation creates secure random token."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()

        assert token1 is not None
        assert token2 is not None
        assert token1 != token2  # Should be different
        assert len(token1) > 64  # URL-safe base64 of 64 bytes is longer

    def test_hash_refresh_token(self):
        """Test refresh token hashing with SHA256."""
        token = "test_refresh_token"
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)

        assert hash1 == hash2  # Same token should produce same hash
        assert len(hash1) == 64  # SHA256 produces 64-character hex

    def test_hash_different_tokens(self):
        """Test different tokens produce different hashes."""
        token1 = "token_1"
        token2 = "token_2"

        hash1 = hash_refresh_token(token1)
        hash2 = hash_refresh_token(token2)

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_create_refresh_token(self):
        """Test refresh token creation stores token in database."""
        user_id = "user_123"

        # Mock the database CRUD function
        with patch('app.database.crud.refresh_tokens.create_refresh_token', new_callable=AsyncMock) as mock_db_create:
            mock_db_create.return_value = None

            token, token_hash = await create_refresh_token(user_id)

            assert token is not None
            assert token_hash is not None
            assert len(token) > 64
            assert len(token_hash) == 64

            # Verify hash matches token
            expected_hash = hash_refresh_token(token)
            assert token_hash == expected_hash

    @pytest.mark.asyncio
    async def test_verify_refresh_token_valid(self):
        """Test refresh token verification with valid token."""
        user_id = "user_123"
        token = "valid_refresh_token"
        token_hash = hash_refresh_token(token)

        refresh_token_data = {
            "user_id": user_id,
            "token_hash": token_hash,
            "revoked": False,
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }

        # Mock the database CRUD functions
        with patch('app.database.crud.refresh_tokens.get_refresh_token_by_hash', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = refresh_token_data

            result = await verify_refresh_token(token)
            assert result == user_id


# ============================================================================
# Password Hashing Tests (5 essential tests from test_password.py)
# ============================================================================

class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_password_produces_different_hashes(self):
        """Test bcrypt produces different hashes for same password (salt effect)."""
        password = "SecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # bcrypt salt makes each hash unique
        assert len(hash1) > 50  # bcrypt hashes are typically 60 characters

    def test_hash_password_not_empty(self):
        """Test password hashing produces non-empty hash."""
        password = "TestPassword"
        hashed = hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0
        assert isinstance(hashed, str)

    def test_hash_password_consistent_length(self):
        """Test bcrypt hashes have consistent length regardless of password length."""
        passwords = ["short", "medium_length_password", "very_long_password_with_many_characters_123456789"]

        hashes = [hash_password(pwd) for pwd in passwords]

        # All bcrypt hashes should have the same length (60 chars)
        hash_lengths = [len(h) for h in hashes]
        assert len(set(hash_lengths)) == 1  # All lengths should be the same

    def test_hash_empty_password(self):
        """Test hashing empty password."""
        password = ""
        hashed = hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0

    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters."""
        password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0


# ============================================================================
# Password Verification Tests (6 essential tests from test_password.py)
# ============================================================================

class TestPasswordVerification:
    """Test password verification."""

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification rejects incorrect password."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        result = verify_password("WrongPassword", hashed)
        assert result is False

    def test_verify_password_case_sensitive(self):
        """Test password verification is case-sensitive."""
        password = "Password123"
        hashed = hash_password(password)

        # Different case should fail
        result = verify_password("password123", hashed)
        assert result is False

        result = verify_password("PASSWORD123", hashed)
        assert result is False

    def test_verify_password_whitespace_sensitive(self):
        """Test password verification is sensitive to whitespace."""
        password = "Password 123"
        hashed = hash_password(password)

        assert verify_password("Password 123", hashed) is True
        assert verify_password("Password123", hashed) is False  # No space
        assert verify_password(" Password 123", hashed) is False  # Leading space

    def test_verify_password_with_invalid_hash(self):
        """Test password verification handles invalid hash format."""
        from passlib.exc import UnknownHashError
        password = "TestPassword"
        invalid_hash = "not_a_valid_bcrypt_hash"

        # Invalid hash should raise exception (passlib behavior)
        with pytest.raises(UnknownHashError):
            verify_password(password, invalid_hash)

    def test_identical_passwords_different_users(self):
        """Test same password for different users produces different hashes."""
        password = "CommonPassword123"

        hash_user1 = hash_password(password)
        hash_user2 = hash_password(password)

        # Same password should produce different hashes (due to salt)
        assert hash_user1 != hash_user2

        # Both hashes should verify correctly
        assert verify_password(password, hash_user1) is True
        assert verify_password(password, hash_user2) is True


# ============================================================================
# User Authentication Tests (4 essential tests from test_password.py)
# ============================================================================

class TestUserAuthentication:
    """Test user authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication."""
        email = "test@example.com"
        password = "SecurePassword123"
        hashed_password = hash_password(password)

        user_dict = create_user_dict(
            id="user_123",
            email=email,
            password=hashed_password,
            name="Test User",
            is_system=False
        )

        with patch('app.core.utils.auth.get_user_by_email') as mock_get_user:
            mock_get_user.return_value = user_dict

            result = await authenticate_user(email, password)

            assert result is not False
            assert result.id == "user_123"
            assert result.email == email

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication fails with wrong password."""
        email = "test@example.com"
        password = "SecurePassword123"
        hashed_password = hash_password(password)

        user_dict = create_user_dict(
            id="user_123",
            email=email,
            password=hashed_password,
            name="Test User",
            is_system=False
        )

        with patch('app.core.utils.auth.get_user_by_email') as mock_get_user:
            mock_get_user.return_value = user_dict

            result = await authenticate_user(email, "WrongPassword")

            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication fails when user doesn't exist."""
        email = "nonexistent@example.com"
        password = "SecurePassword123"

        with patch('app.core.utils.auth.get_user_by_email') as mock_get_user:
            mock_get_user.return_value = None

            result = await authenticate_user(email, password)

            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_user_case_sensitive_email(self):
        """Test authentication email lookup behavior."""
        email = "test@example.com"
        password = "SecurePassword123"
        hashed_password = hash_password(password)

        user_dict = create_user_dict(
            id="user_123",
            email=email,
            password=hashed_password,
            name="Test User",
            is_system=False
        )

        with patch('app.core.utils.auth.get_user_by_email') as mock_get_user:
            # Mock should be called with exact email provided
            mock_get_user.return_value = user_dict

            result = await authenticate_user("TEST@EXAMPLE.COM", password)

            # Verify the function was called with the exact case provided
            mock_get_user.assert_called_once_with("TEST@EXAMPLE.COM")


# ============================================================================
# Current User Retrieval Tests (3 tests for get_current_user)
# ============================================================================

class TestCurrentUserRetrieval:
    """Test current user retrieval from request cookies."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful current user retrieval from cookie."""
        from fastapi import HTTPException
        from app.core.utils.auth import get_current_user

        user_id = "user_123"
        token = create_access_token({"sub": user_id}, expires_delta=timedelta(hours=1))

        user_dict = create_user_dict(
            id=user_id,
            email="test@example.com",
            name="Test User"
        )

        # Mock request with cookie
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token

        with patch('app.core.utils.auth.get_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = user_dict

            user = await get_current_user(mock_request)

            assert user.id == user_id
            assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_no_cookie(self):
        """Test get_current_user raises 401 when no cookie present."""
        from fastapi import HTTPException
        from app.core.utils.auth import get_current_user

        # Mock request without cookie
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user raises 401 with invalid token."""
        from fastapi import HTTPException
        from app.core.utils.auth import get_current_user

        # Mock request with invalid token
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        """Test get_current_user raises 401 when user doesn't exist."""
        from fastapi import HTTPException
        from app.core.utils.auth import get_current_user

        user_id = "nonexistent_user"
        token = create_access_token({"sub": user_id}, expires_delta=timedelta(hours=1))

        # Mock request with valid token
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token

        with patch('app.core.utils.auth.get_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail
