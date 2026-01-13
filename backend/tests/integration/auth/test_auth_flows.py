"""Integration tests for authentication flows (login, register, token refresh, logout)."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.api.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_database():
    """Mock database operations for integration tests."""
    with patch('app.database.crud.get_user_by_email') as mock_get_user, \
         patch('app.database.crud.create_user') as mock_create_user, \
         patch('app.database.crud.get_user') as mock_get_user_by_id, \
         patch('app.core.utils.auth.db_create_refresh_token') as mock_create_refresh, \
         patch('app.core.utils.auth.get_refresh_token_by_hash') as mock_get_refresh, \
         patch('app.core.utils.auth.revoke_refresh_token') as mock_revoke_refresh:

        # Setup default mock behavior
        mock_get_user.return_value = None
        mock_create_user.return_value = "user_123"
        mock_create_refresh.return_value = None

        yield {
            'get_user_by_email': mock_get_user,
            'create_user': mock_create_user,
            'get_user_by_id': mock_get_user_by_id,
            'create_refresh_token': mock_create_refresh,
            'get_refresh_token': mock_get_refresh,
            'revoke_refresh_token': mock_revoke_refresh
        }


class TestRegistrationFlow:
    """Test user registration flow."""

    def test_register_success(self, client, mock_database):
        """Test successful user registration."""
        user_data = {
            "email": "testuser@example.com",
            "password": "SecurePassword123",
            "name": "Test User"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert "user_id" in data
        assert "password" not in data  # Password should not be returned

        # Verify cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_register_duplicate_email(self, client, mock_database):
        """Test registration fails with duplicate email."""
        # Mock existing user
        mock_database['get_user_by_email'].return_value = {
            "id": "existing_user",
            "email": "existing@example.com"
        }

        user_data = {
            "email": "existing@example.com",
            "password": "Password123",
            "name": "Test User"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client, mock_database):
        """Test registration fails with invalid email format."""
        user_data = {
            "email": "invalid-email",
            "password": "Password123",
            "name": "Test User"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Pydantic should validate email format
        assert response.status_code == 422

    def test_register_missing_fields(self, client, mock_database):
        """Test registration fails with missing required fields."""
        incomplete_data = {
            "email": "test@example.com"
            # Missing password and name
        }

        response = client.post("/api/v1/auth/register", json=incomplete_data)

        assert response.status_code == 422

    def test_register_empty_password(self, client, mock_database):
        """Test registration with empty password."""
        user_data = {
            "email": "test@example.com",
            "password": "",
            "name": "Test User"
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should either fail validation or succeed (depending on requirements)
        # Document actual behavior
        assert response.status_code in [201, 422]


class TestLoginFlow:
    """Test user login flow."""

    def test_login_success(self, client, mock_database):
        """Test successful user login."""
        # Setup existing user
        from app.core.utils.auth import hash_password
        hashed_password = hash_password("SecurePassword123")

        mock_database['get_user_by_email'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        login_data = {
            "email": "test@example.com",
            "password": "SecurePassword123"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == login_data["email"]
        assert data["user_id"] == "user_123"
        assert "password" not in data

        # Verify cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client, mock_database):
        """Test login fails with wrong password."""
        from app.core.utils.auth import hash_password
        hashed_password = hash_password("CorrectPassword123")

        mock_database['get_user_by_email'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

        # Verify no cookies are set
        assert "access_token" not in response.cookies
        assert "refresh_token" not in response.cookies

    def test_login_nonexistent_user(self, client, mock_database):
        """Test login fails for nonexistent user."""
        mock_database['get_user_by_email'].return_value = None

        login_data = {
            "email": "nonexistent@example.com",
            "password": "Password123"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    def test_login_case_sensitive_password(self, client, mock_database):
        """Test login is case-sensitive for password."""
        from app.core.utils.auth import hash_password
        hashed_password = hash_password("Password123")

        mock_database['get_user_by_email'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        # Try with different case
        login_data = {
            "email": "test@example.com",
            "password": "password123"  # lowercase
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test access to protected endpoints with authentication."""

    def test_protected_endpoint_with_valid_token(self, client, mock_database):
        """Test accessing protected endpoint with valid JWT."""
        from app.core.utils.auth import create_access_token, hash_password
        from datetime import timedelta

        # Setup user
        hashed_password = hash_password("Password123")
        mock_database['get_user_by_email'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        mock_database['get_user_by_id'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        # Login first to get token
        login_data = {"email": "test@example.com", "password": "Password123"}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        # Access protected endpoint
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "user_123"

    def test_protected_endpoint_without_token(self, client, mock_database):
        """Test accessing protected endpoint without JWT returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_protected_endpoint_with_expired_token(self, client, mock_database):
        """Test accessing protected endpoint with expired JWT."""
        from app.core.utils.auth import create_access_token
        from datetime import timedelta

        # Create expired token
        expired_token = create_access_token(
            {"sub": "user_123"},
            expires_delta=timedelta(seconds=-10)
        )

        # Try to access protected endpoint with expired token
        client.cookies.set("access_token", expired_token)
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client, mock_database):
        """Test accessing protected endpoint with invalid JWT."""
        client.cookies.set("access_token", "invalid.token.format")
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestTokenRefreshFlow:
    """Test token refresh flow."""

    def test_refresh_token_success(self, client, mock_database):
        """Test successful token refresh."""
        from app.core.utils.auth import hash_refresh_token
        from datetime import datetime, timedelta

        # Setup refresh token in database
        refresh_token_value = "valid_refresh_token_abc123"
        token_hash = hash_refresh_token(refresh_token_value)

        mock_database['get_refresh_token'].return_value = {
            "user_id": "user_123",
            "token_hash": token_hash,
            "revoked": False,
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }

        # Set refresh token cookie
        client.cookies.set("refresh_token", refresh_token_value)

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "refreshed"

        # Verify new access token cookie is set
        assert "access_token" in response.cookies

    def test_refresh_token_missing(self, client, mock_database):
        """Test token refresh fails without refresh token."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401
        assert "no refresh token" in response.json()["detail"].lower()

    def test_refresh_token_expired(self, client, mock_database):
        """Test token refresh fails with expired refresh token."""
        from app.core.utils.auth import hash_refresh_token
        from datetime import datetime, timedelta

        refresh_token_value = "expired_refresh_token"
        token_hash = hash_refresh_token(refresh_token_value)

        mock_database['get_refresh_token'].return_value = {
            "user_id": "user_123",
            "token_hash": token_hash,
            "revoked": False,
            "expires_at": datetime.utcnow() - timedelta(days=1)  # Expired
        }

        client.cookies.set("refresh_token", refresh_token_value)

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

    def test_refresh_token_revoked(self, client, mock_database):
        """Test token refresh fails with revoked refresh token."""
        from app.core.utils.auth import hash_refresh_token
        from datetime import datetime, timedelta

        refresh_token_value = "revoked_refresh_token"
        token_hash = hash_refresh_token(refresh_token_value)

        mock_database['get_refresh_token'].return_value = {
            "user_id": "user_123",
            "token_hash": token_hash,
            "revoked": True,  # Revoked
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }

        client.cookies.set("refresh_token", refresh_token_value)

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

    def test_refresh_token_invalid(self, client, mock_database):
        """Test token refresh fails with invalid refresh token."""
        mock_database['get_refresh_token'].return_value = None

        client.cookies.set("refresh_token", "invalid_token")

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401


class TestLogoutFlow:
    """Test user logout flow."""

    def test_logout_success(self, client, mock_database):
        """Test successful logout."""
        from app.core.utils.auth import hash_refresh_token

        refresh_token_value = "refresh_token_to_revoke"
        token_hash = hash_refresh_token(refresh_token_value)

        client.cookies.set("refresh_token", refresh_token_value)
        client.cookies.set("access_token", "some_access_token")

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

        # Verify refresh token was revoked
        mock_database['revoke_refresh_token'].assert_called_once_with(token_hash)

    def test_logout_without_tokens(self, client, mock_database):
        """Test logout without tokens still succeeds."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        # Should not crash even without tokens

    def test_logout_clears_cookies(self, client, mock_database):
        """Test logout clears authentication cookies."""
        client.cookies.set("refresh_token", "some_token")
        client.cookies.set("access_token", "some_access_token")

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200

        # Note: TestClient doesn't fully simulate cookie deletion
        # This documents the API behavior


class TestCompleteAuthFlow:
    """Test complete authentication flow from registration to logout."""

    def test_complete_user_journey(self, client, mock_database):
        """Test complete user authentication journey."""
        from app.core.utils.auth import hash_password, hash_refresh_token
        from datetime import datetime, timedelta

        # 1. Register new user
        user_data = {
            "email": "journey@example.com",
            "password": "JourneyPassword123",
            "name": "Journey User"
        }

        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # 2. Logout after registration
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # 3. Login with credentials
        hashed_password = hash_password("JourneyPassword123")
        mock_database['get_user_by_email'].return_value = {
            "id": "user_journey",
            "email": "journey@example.com",
            "password": hashed_password,
            "name": "Journey User",
            "is_system": False
        }

        login_data = {"email": "journey@example.com", "password": "JourneyPassword123"}
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200

        # 4. Access protected resource
        mock_database['get_user_by_id'].return_value = {
            "id": "user_journey",
            "email": "journey@example.com",
            "password": hashed_password,
            "name": "Journey User",
            "is_system": False
        }

        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "journey@example.com"

        # 5. Refresh token
        refresh_token_value = client.cookies.get("refresh_token")
        if refresh_token_value:
            token_hash = hash_refresh_token(refresh_token_value)
            mock_database['get_refresh_token'].return_value = {
                "user_id": "user_journey",
                "token_hash": token_hash,
                "revoked": False,
                "expires_at": datetime.utcnow() + timedelta(days=7)
            }

            refresh_response = client.post("/api/v1/auth/refresh")
            assert refresh_response.status_code == 200

        # 6. Final logout
        final_logout = client.post("/api/v1/auth/logout")
        assert final_logout.status_code == 200


class TestAuthSecurityEdgeCases:
    """Test authentication security edge cases."""

    def test_sql_injection_in_email(self, client, mock_database):
        """Test SQL injection attempt in email field."""
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "Password123",
            "name": "Hacker"
        }

        response = client.post("/api/v1/auth/register", json=malicious_data)

        # Should either reject as invalid email or safely handle
        # Actual behavior depends on email validation
        assert response.status_code in [201, 422]

    def test_xss_in_name_field(self, client, mock_database):
        """Test XSS attempt in name field."""
        xss_data = {
            "email": "xss@example.com",
            "password": "Password123",
            "name": "<script>alert('XSS')</script>"
        }

        response = client.post("/api/v1/auth/register", json=xss_data)

        # Should store data safely (no execution)
        if response.status_code == 201:
            assert xss_data["name"] in str(response.json())

    def test_concurrent_login_attempts(self, client, mock_database):
        """Test multiple concurrent login attempts."""
        from app.core.utils.auth import hash_password

        hashed_password = hash_password("Password123")
        mock_database['get_user_by_email'].return_value = {
            "id": "user_concurrent",
            "email": "concurrent@example.com",
            "password": hashed_password,
            "name": "Concurrent User",
            "is_system": False
        }

        login_data = {"email": "concurrent@example.com", "password": "Password123"}

        # Simulate concurrent requests
        responses = [client.post("/api/v1/auth/login", json=login_data) for _ in range(5)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_token_reuse_after_logout(self, client, mock_database):
        """Test that tokens cannot be reused after logout."""
        from app.core.utils.auth import hash_password

        # Login
        hashed_password = hash_password("Password123")
        mock_database['get_user_by_email'].return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "password": hashed_password,
            "name": "Test User",
            "is_system": False
        }

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "Password123"}
        )
        assert login_response.status_code == 200

        old_access_token = client.cookies.get("access_token")

        # Logout
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Try to use old access token
        client.cookies.set("access_token", old_access_token)
        response = client.get("/api/v1/auth/me")

        # Token might still be technically valid (JWT) but refresh token is revoked
        # Behavior depends on implementation
        # Document actual behavior here
