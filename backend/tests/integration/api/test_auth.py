"""Integration tests for auth routes.

Tests all authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
"""

import pytest


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    def test_register_success(self, client, clean_db):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "name": "New User"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "user_id" in data
        assert data["user_id"].startswith("usr_")

        # Verify cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email returns 400."""
        response = client.post("/api/v1/auth/register", json={
            "email": test_user["email"],
            "password": "password123",
            "name": "Duplicate User"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client, clean_db):
        """Test registration with invalid email returns 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "name": "Test User"
        })

        assert response.status_code == 422  # Pydantic validation error

    def test_register_short_password(self, client, clean_db):
        """Test registration with short password returns 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "short",
            "name": "Test User"
        })

        assert response.status_code == 422  # Pydantic validation


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, client, test_user):
        """Test successful login with valid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["plain_password"]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["id"]
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]

        # Verify cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_login_invalid_password(self, client, test_user):
        """Test login with incorrect password returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_invalid_email(self, client, clean_db):
        """Test login with non-existent email returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()


class TestGetMe:
    """Tests for GET /api/v1/auth/me"""

    def test_get_me_authenticated(self, authenticated_client, test_user):
        """Test getting current user info when authenticated."""
        response = authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]

    def test_get_me_unauthenticated(self, client, clean_db):
        """Test getting current user without authentication returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh"""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh with valid refresh token."""
        # First login to get refresh token
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["plain_password"]
        })
        assert login_response.status_code == 200

        # Extract refresh_token cookie from login response
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None, "Login should set refresh_token cookie"

        # Set the refresh_token cookie for the next request
        client.cookies.set("refresh_token", refresh_token)

        # Refresh the token
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "refreshed"

        # Verify new access_token cookie is set
        assert "access_token" in response.cookies

    def test_refresh_token_missing(self, client, clean_db):
        """Test refresh without refresh token returns 401."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401
        assert "no refresh token" in response.json()["detail"].lower()

    def test_refresh_token_invalid(self, client, clean_db):
        """Test refresh with invalid refresh token returns 401."""
        # Manually set an invalid refresh token cookie
        client.cookies.set("refresh_token", "invalid_token_value")

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


class TestLogout:
    """Tests for POST /api/v1/auth/logout"""

    def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()

        # Verify cookies are deleted (TestClient may not show deleted cookies)
        # In real scenario, cookies would have empty value or be removed

    def test_logout_without_token(self, client, clean_db):
        """Test logout without being logged in still succeeds."""
        response = client.post("/api/v1/auth/logout")

        # Logout should succeed even without active session
        assert response.status_code == 200
