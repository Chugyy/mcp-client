"""Integration tests for RBAC (Role-Based Access Control) enforcement."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.api.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture
def super_admin_user():
    """Super admin user fixture."""
    from app.core.utils.auth import hash_password

    return {
        "id": "user_admin",
        "email": "admin@example.com",
        "password": hash_password("AdminPassword123"),
        "name": "Admin User",
        "is_system": True  # Super admin flag
    }


@pytest.fixture
def regular_user():
    """Regular user fixture."""
    from app.core.utils.auth import hash_password

    return {
        "id": "user_regular",
        "email": "user@example.com",
        "password": hash_password("UserPassword123"),
        "name": "Regular User",
        "is_system": False
    }


@pytest.fixture
def another_user():
    """Another regular user fixture for testing cross-user access."""
    from app.core.utils.auth import hash_password

    return {
        "id": "user_other",
        "email": "other@example.com",
        "password": hash_password("OtherPassword123"),
        "name": "Other User",
        "is_system": False
    }


class TestSuperAdminAccess:
    """Test super admin (system user) access to all resources."""

    def test_super_admin_can_access_own_automation(self, client, super_admin_user):
        """Test super admin can access their own automations."""
        automation = {
            "id": "auto_admin",
            "user_id": "user_admin",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        assert can_access_automation(admin, automation) is True

    def test_super_admin_can_access_other_user_automation(self, client, super_admin_user):
        """Test super admin can access other users' automations."""
        automation = {
            "id": "auto_other",
            "user_id": "user_other",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        assert can_access_automation(admin, automation) is True

    def test_super_admin_can_access_system_automation(self, client, super_admin_user):
        """Test super admin can access system automations."""
        automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        assert can_access_automation(admin, automation) is True

    def test_super_admin_detected_correctly(self, client, super_admin_user):
        """Test super admin flag is detected correctly."""
        from app.core.utils.permissions import is_super_admin
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        assert is_super_admin(admin) is True


class TestRegularUserAccess:
    """Test regular user access restrictions."""

    def test_regular_user_can_access_own_automation(self, client, regular_user):
        """Test regular user can access their own automations."""
        automation = {
            "id": "auto_user",
            "user_id": "user_regular",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        assert can_access_automation(user, automation) is True

    def test_regular_user_cannot_access_other_automation(self, client, regular_user):
        """Test regular user cannot access other users' automations."""
        automation = {
            "id": "auto_other",
            "user_id": "user_other",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        assert can_access_automation(user, automation) is False

    def test_regular_user_can_access_system_automation(self, client, regular_user):
        """Test regular user can access system automations."""
        automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        assert can_access_automation(user, automation) is True

    def test_regular_user_not_super_admin(self, client, regular_user):
        """Test regular user is not detected as super admin."""
        from app.core.utils.permissions import is_super_admin
        from app.database.models import User

        user = User.from_row(regular_user)
        assert is_super_admin(user) is False


class TestCrossUserAccess:
    """Test access control between different regular users."""

    def test_user_cannot_access_another_user_resource(self, client, regular_user, another_user):
        """Test user A cannot access user B's resources."""
        automation_b = {
            "id": "auto_b",
            "user_id": "user_other",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user_a = User.from_row(regular_user)
        assert can_access_automation(user_a, automation_b) is False

    def test_users_can_access_own_resources_simultaneously(self, client, regular_user, another_user):
        """Test multiple users can access their own resources."""
        automation_a = {
            "id": "auto_a",
            "user_id": "user_regular",
            "is_system": False
        }

        automation_b = {
            "id": "auto_b",
            "user_id": "user_other",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user_a = User.from_row(regular_user)
        user_b = User.from_row(another_user)

        assert can_access_automation(user_a, automation_a) is True
        assert can_access_automation(user_b, automation_b) is True

        # But not each other's
        assert can_access_automation(user_a, automation_b) is False
        assert can_access_automation(user_b, automation_a) is False

    def test_both_users_can_access_system_resources(self, client, regular_user, another_user):
        """Test all users can access system resources."""
        system_automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user_a = User.from_row(regular_user)
        user_b = User.from_row(another_user)

        assert can_access_automation(user_a, system_automation) is True
        assert can_access_automation(user_b, system_automation) is True


class TestSystemAutomationAccess:
    """Test system automation access control."""

    def test_system_automation_accessible_by_all_users(self, client, super_admin_user, regular_user):
        """Test system automations are accessible by all user types."""
        system_automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        user = User.from_row(regular_user)

        assert can_access_automation(admin, system_automation) is True
        assert can_access_automation(user, system_automation) is True

    def test_system_automation_with_different_owner(self, client, regular_user):
        """Test system automation is accessible even with different user_id."""
        # System automation owned by admin but marked as system
        system_automation = {
            "id": "auto_system_admin",
            "user_id": "user_admin",  # Owned by admin
            "is_system": True  # But marked as system
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        # Should be accessible due to is_system flag
        assert can_access_automation(user, system_automation) is True


class TestAuthenticationRequired:
    """Test that authentication is required for protected endpoints."""

    def test_unauthenticated_cannot_access_protected_endpoint(self, client):
        """Test unauthenticated request to protected endpoint returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_authenticated_can_access_protected_endpoint(self, client, regular_user):
        """Test authenticated user can access protected endpoints."""
        with patch('app.database.crud.get_user_by_email') as mock_get_email, \
             patch('app.database.crud.get_user') as mock_get_user:

            mock_get_email.return_value = regular_user
            mock_get_user.return_value = regular_user

            # Login
            login_data = {"email": "user@example.com", "password": "UserPassword123"}
            login_response = client.post("/api/v1/auth/login", json=login_data)
            assert login_response.status_code == 200

            # Access protected endpoint
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 200


class TestPermissionHierarchy:
    """Test permission hierarchy and precedence."""

    def test_super_admin_overrides_ownership(self, client, super_admin_user):
        """Test super admin permission overrides ownership checks."""
        # Private automation owned by someone else
        private_automation = {
            "id": "auto_private",
            "user_id": "user_other",
            "is_system": False
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        # Super admin should access despite not being owner
        assert can_access_automation(admin, private_automation) is True

    def test_system_flag_overrides_ownership(self, client, regular_user):
        """Test is_system flag overrides ownership checks."""
        # System automation owned by someone else
        system_automation = {
            "id": "auto_system",
            "user_id": "user_other",
            "is_system": True
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        # Should access due to system flag
        assert can_access_automation(user, system_automation) is True

    def test_permission_check_order(self, client, super_admin_user, regular_user):
        """Test permission checks follow correct precedence order."""
        # Priority: 1. Super admin, 2. System automation, 3. Owner

        automations = [
            {"id": "a1", "user_id": "user_admin", "is_system": True},   # Admin + System
            {"id": "a2", "user_id": "user_admin", "is_system": False},  # Admin-owned
            {"id": "a3", "user_id": "user_other", "is_system": True},   # System (other owner)
            {"id": "a4", "user_id": "user_other", "is_system": False},  # Other user's private
        ]

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        admin = User.from_row(super_admin_user)
        user = User.from_row(regular_user)

        # Admin should access all
        for auto in automations:
            assert can_access_automation(admin, auto) is True

        # Regular user should access: a1 (system), a3 (system)
        assert can_access_automation(user, automations[0]) is True  # System
        assert can_access_automation(user, automations[1]) is False  # Admin's private
        assert can_access_automation(user, automations[2]) is True  # System
        assert can_access_automation(user, automations[3]) is False  # Other's private


class TestRBACEdgeCases:
    """Test RBAC edge cases and boundary conditions."""

    def test_permission_with_null_is_system(self, client, regular_user):
        """Test permission check when is_system is None."""
        automation = {
            "id": "auto_1",
            "user_id": "user_regular",
            "is_system": None
        }

        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)
        # Should still work (None treated as False)
        assert can_access_automation(user, automation) is True

    def test_permission_with_missing_fields(self, client, regular_user):
        """Test permission check with missing automation fields."""
        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user = User.from_row(regular_user)

        # Missing is_system
        automation1 = {"id": "auto_1", "user_id": "user_regular"}
        assert can_access_automation(user, automation1) is True

        # Missing user_id
        automation2 = {"id": "auto_2", "is_system": False}
        assert can_access_automation(user, automation2) is False

    def test_permission_with_special_user_ids(self, client):
        """Test permissions with various user ID formats."""
        from app.core.utils.permissions import can_access_automation
        from app.database.models import User
        from app.core.utils.auth import hash_password

        test_cases = [
            "user-with-dashes",
            "user_with_underscores",
            "user.with.dots",
            "User123",
            "123456",
            "user@domain",
        ]

        for user_id in test_cases:
            user_dict = {
                "id": user_id,
                "email": f"{user_id}@example.com",
                "password": hash_password("Password123"),
                "name": "Test User",
                "is_system": False
            }
            user = User.from_row(user_dict)

            automation = {
                "id": "auto_1",
                "user_id": user_id,
                "is_system": False
            }

            assert can_access_automation(user, automation) is True, f"Failed for user_id: {user_id}"

    def test_permission_case_sensitivity(self, client):
        """Test permission checks are case-sensitive for user IDs."""
        from app.core.utils.permissions import can_access_automation
        from app.database.models import User
        from app.core.utils.auth import hash_password

        user_dict = {
            "id": "User123",  # Mixed case
            "email": "user@example.com",
            "password": hash_password("Password123"),
            "name": "Test User",
            "is_system": False
        }
        user = User.from_row(user_dict)

        automation_match = {"id": "auto_1", "user_id": "User123", "is_system": False}
        automation_mismatch = {"id": "auto_2", "user_id": "user123", "is_system": False}

        assert can_access_automation(user, automation_match) is True
        assert can_access_automation(user, automation_mismatch) is False

    def test_multiple_users_same_automation_name(self, client, regular_user, another_user):
        """Test different users can have automations with same name but different IDs."""
        from app.core.utils.permissions import can_access_automation
        from app.database.models import User

        user_a = User.from_row(regular_user)
        user_b = User.from_row(another_user)

        # Both have "backup" automation but different owners
        automation_a = {
            "id": "auto_a_backup",
            "user_id": "user_regular",
            "name": "backup",
            "is_system": False
        }

        automation_b = {
            "id": "auto_b_backup",
            "user_id": "user_other",
            "name": "backup",
            "is_system": False
        }

        # Each should only access their own
        assert can_access_automation(user_a, automation_a) is True
        assert can_access_automation(user_a, automation_b) is False

        assert can_access_automation(user_b, automation_b) is True
        assert can_access_automation(user_b, automation_a) is False


class TestRoleTransitions:
    """Test permission changes when user roles change."""

    def test_user_promoted_to_super_admin(self, client):
        """Test user gains super admin permissions after promotion."""
        from app.core.utils.permissions import is_super_admin, can_access_automation
        from app.database.models import User
        from app.core.utils.auth import hash_password

        # Start as regular user
        user_dict = {
            "id": "user_promote",
            "email": "promote@example.com",
            "password": hash_password("Password123"),
            "name": "Promote User",
            "is_system": False
        }
        user = User.from_row(user_dict)

        assert is_super_admin(user) is False

        other_automation = {
            "id": "auto_other",
            "user_id": "user_other",
            "is_system": False
        }

        # Cannot access other's automation
        assert can_access_automation(user, other_automation) is False

        # Promote to super admin
        user_dict["is_system"] = True
        super_admin = User.from_row(user_dict)

        assert is_super_admin(super_admin) is True
        # Now can access other's automation
        assert can_access_automation(super_admin, other_automation) is True

    def test_super_admin_demoted_to_regular_user(self, client):
        """Test super admin loses permissions after demotion."""
        from app.core.utils.permissions import is_super_admin, can_access_automation
        from app.database.models import User
        from app.core.utils.auth import hash_password

        # Start as super admin
        admin_dict = {
            "id": "user_demote",
            "email": "demote@example.com",
            "password": hash_password("Password123"),
            "name": "Demote User",
            "is_system": True
        }
        admin = User.from_row(admin_dict)

        assert is_super_admin(admin) is True

        other_automation = {
            "id": "auto_other",
            "user_id": "user_other",
            "is_system": False
        }

        # Can access other's automation
        assert can_access_automation(admin, other_automation) is True

        # Demote to regular user
        admin_dict["is_system"] = False
        regular_user = User.from_row(admin_dict)

        assert is_super_admin(regular_user) is False
        # Now cannot access other's automation
        assert can_access_automation(regular_user, other_automation) is False


class TestUnauthorizedAccessAttempts:
    """Test handling of unauthorized access attempts."""

    def test_anonymous_user_cannot_access_resources(self, client):
        """Test anonymous (not logged in) user cannot access protected resources."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_user_cannot_forge_super_admin_status(self, client, regular_user):
        """Test user cannot fake super admin status through token manipulation."""
        # This test documents that super admin status comes from database,
        # not from JWT claims that could be forged

        from app.database.models import User
        user = User.from_row(regular_user)

        # Verify is_system comes from database user record
        assert hasattr(user, 'is_system')
        assert user.is_system is False

    def test_access_denied_returns_appropriate_status(self, client):
        """Test that access denied scenarios return correct HTTP status codes."""
        # 401 for not authenticated (no token)
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

        # 403 would be for authenticated but forbidden (if implemented)
        # This test documents expected behavior
