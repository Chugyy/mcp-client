"""Integration tests for users routes.

Tests all user profile endpoints:
- GET /api/v1/users/me
- PATCH /api/v1/users/me
- DELETE /api/v1/users/me
"""

import pytest


class TestGetMe:
    """Tests for GET /api/v1/users/me"""

    def test_get_me_authenticated(self, authenticated_client, test_user):
        """Test getting current user info when authenticated."""
        response = authenticated_client.get("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]
        assert "preferences" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_me_unauthenticated(self, client, clean_db):
        """Test getting current user without authentication returns 401."""
        response = client.get("/api/v1/users/me")

        assert response.status_code == 401


class TestUpdateMe:
    """Tests for PATCH /api/v1/users/me"""

    def test_update_me_success(self, authenticated_client, test_user):
        """Test successful user profile update."""
        response = authenticated_client.patch("/api/v1/users/me", json={
            "name": "Updated Name",
            "preferences": {"theme": "dark", "language": "en"}
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["preferences"]["theme"] == "dark"
        assert data["preferences"]["language"] == "en"
        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]

    def test_update_me_partial(self, authenticated_client, test_user):
        """Test partial user profile update (name only)."""
        response = authenticated_client.patch("/api/v1/users/me", json={
            "name": "New Name Only"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name Only"
        assert data["id"] == test_user["id"]

    def test_update_me_invalid_data(self, authenticated_client):
        """Test updating user with invalid data returns 422."""
        # Send invalid JSON structure (name as integer instead of string)
        response = authenticated_client.patch("/api/v1/users/me", json={
            "name": 12345,  # Should be a string
            "preferences": "not_a_dict"  # Should be a dict
        })

        assert response.status_code == 422  # Pydantic validation error


class TestDeleteMe:
    """Tests for DELETE /api/v1/users/me"""

    def test_delete_me_success(self, authenticated_client, test_user):
        """Test successful user account deletion."""
        response = authenticated_client.delete("/api/v1/users/me")

        assert response.status_code == 204
        # 204 No Content should have no response body
        assert response.text == ""

        # Verify user can no longer access their account
        get_response = authenticated_client.get("/api/v1/users/me")
        assert get_response.status_code == 401  # User should be deleted, token invalid
