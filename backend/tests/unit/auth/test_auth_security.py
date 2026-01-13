"""Authentication security tests: RBAC permissions + API key encryption.

Consolidated from test_permissions.py and test_api_keys.py.
Focuses on essential security functionality with 70-80% coverage target.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from cryptography.fernet import Fernet

from datetime import datetime

from app.core.utils.permissions import is_super_admin, can_access_automation
from app.core.utils.encryption import encrypt_api_key, decrypt_api_key, _get_fernet
from app.database.crud.api_keys import (
    create_api_key,
    get_api_key,
    get_api_key_decrypted,
    list_api_keys,
    update_api_key,
    delete_api_key
)
from app.database.models import User


# Helper class for async context manager mocking
class AsyncMockContextManager:
    """Helper to create async context manager from mock."""
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


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
# Super Admin Permissions (5 essential tests from test_permissions.py)
# ============================================================================

class TestSuperAdminPermissions:
    """Test super admin (system user) permission checks."""

    def test_is_super_admin_true(self):
        """Test super admin detection for system user."""
        user_dict = create_user_dict(
            id="user_system",
            email="system@example.com",
            name="System User",
            is_system=True
        )
        user = User.from_row(user_dict)

        assert is_super_admin(user) is True

    def test_is_super_admin_false(self):
        """Test super admin detection for regular user."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="Regular User",
            is_system=False
        )
        user = User.from_row(user_dict)

        assert is_super_admin(user) is False

    def test_is_super_admin_missing_attribute(self):
        """Test super admin detection when is_system attribute is missing."""
        # Create a minimal user object without is_system
        # getattr() with default returns False when attribute is missing
        user = MagicMock(spec=['id', 'email'])  # Explicitly exclude is_system
        user.id = "user_123"
        user.email = "user@example.com"

        result = is_super_admin(user)
        assert result is False

    def test_is_super_admin_none_value(self):
        """Test super admin detection when is_system is None (treated as False)."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User"
        )
        # Override is_system with None after dict creation
        user_dict["is_system"] = None

        # User.from_row() converts None to False via .get() default
        # But if passed explicitly, it stays None. Let's test the actual behavior
        user = User.from_row(user_dict)

        # None is falsy, so function should treat it as False
        result = is_super_admin(user)
        # getattr returns None, which is falsy but function returns the value directly
        # So we test that None or False are both falsy (not explicitly False)
        assert not result  # None or False are both falsy

    def test_permission_with_none_user(self):
        """Test permission check with None user - getattr handles None gracefully."""
        # getattr(None, 'is_system', False) returns False (doesn't raise AttributeError)
        # This is Python's getattr() behavior - only raises if default not provided
        result = is_super_admin(None)
        assert result is False  # getattr handles None with default


# ============================================================================
# Automation Access Permissions (8 essential tests from test_permissions.py)
# ============================================================================

class TestAutomationPermissions:
    """Test automation resource access permissions."""

    def test_super_admin_can_access_any_automation(self):
        """Test super admin has access to all automations."""
        super_admin_dict = create_user_dict(
            id="user_system",
            email="system@example.com",
            name="System",
            is_system=True
        )
        super_admin = User.from_row(super_admin_dict)

        # Super admin should access any automation
        automation1 = {"id": "auto_1", "user_id": "other_user", "is_system": False}
        automation2 = {"id": "auto_2", "user_id": "another_user", "is_system": False}
        automation3 = {"id": "auto_3", "user_id": "user_system", "is_system": True}

        assert can_access_automation(super_admin, automation1) is True
        assert can_access_automation(super_admin, automation2) is True
        assert can_access_automation(super_admin, automation3) is True

    def test_user_can_access_own_automation(self):
        """Test user can access their own automation."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        user = User.from_row(user_dict)

        automation = {
            "id": "auto_1",
            "user_id": "user_123",
            "is_system": False
        }

        assert can_access_automation(user, automation) is True

    def test_user_cannot_access_other_user_automation(self):
        """Test user cannot access another user's automation."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        user = User.from_row(user_dict)

        automation = {
            "id": "auto_1",
            "user_id": "other_user",
            "is_system": False
        }

        assert can_access_automation(user, automation) is False

    def test_any_user_can_access_system_automation(self):
        """Test any user can access system automations."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        user = User.from_row(user_dict)

        system_automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        assert can_access_automation(user, system_automation) is True

    def test_access_automation_missing_is_system(self):
        """Test automation access when is_system field is missing."""
        user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        user = User.from_row(user_dict)

        # Automation without is_system field (should default to False)
        automation = {
            "id": "auto_1",
            "user_id": "user_123"
            # is_system missing
        }

        # Should be able to access own automation
        assert can_access_automation(user, automation) is True

        # Cannot access other user's automation without is_system=True
        automation["user_id"] = "other_user"
        assert can_access_automation(user, automation) is False

    def test_access_multiple_automations(self):
        """Test access to multiple automations with different ownership."""
        user1_dict = create_user_dict(
            id="user_1",
            email="user1@example.com",
            name="User 1",
            is_system=False
        )
        user1 = User.from_row(user1_dict)

        automations = [
            {"id": "auto_1", "user_id": "user_1", "is_system": False},  # Own
            {"id": "auto_2", "user_id": "user_2", "is_system": False},  # Other's
            {"id": "auto_3", "user_id": "system", "is_system": True},   # System
            {"id": "auto_4", "user_id": "user_3", "is_system": False},  # Other's
            {"id": "auto_5", "user_id": "user_1", "is_system": True},   # Own + System
        ]

        expected_access = [True, False, True, False, True]

        for automation, expected in zip(automations, expected_access):
            result = can_access_automation(user1, automation)
            assert result == expected, f"Failed for automation {automation['id']}"

    def test_permission_hierarchy(self):
        """Test permission hierarchy: super admin > system automation > owner."""
        # Create users
        super_admin_dict = create_user_dict(
            id="admin",
            email="admin@example.com",
            name="Admin",
            is_system=True
        )
        super_admin = User.from_row(super_admin_dict)

        regular_user_dict = create_user_dict(
            id="user_123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        regular_user = User.from_row(regular_user_dict)

        # Private automation owned by regular user
        private_automation = {
            "id": "auto_private",
            "user_id": "user_123",
            "is_system": False
        }

        # Super admin can access private automation
        assert can_access_automation(super_admin, private_automation) is True

        # Regular user can access their own
        assert can_access_automation(regular_user, private_automation) is True

        # System automation accessible by both
        system_automation = {
            "id": "auto_system",
            "user_id": "system",
            "is_system": True
        }

        assert can_access_automation(super_admin, system_automation) is True
        assert can_access_automation(regular_user, system_automation) is True

    def test_permission_case_sensitive_user_ids(self):
        """Test permissions are case-sensitive for user IDs."""
        user_dict = create_user_dict(
            id="User123",
            email="user@example.com",
            name="User",
            is_system=False
        )
        user = User.from_row(user_dict)

        automation1 = {"id": "auto_1", "user_id": "User123", "is_system": False}
        automation2 = {"id": "auto_2", "user_id": "user123", "is_system": False}

        assert can_access_automation(user, automation1) is True
        assert can_access_automation(user, automation2) is False  # Case mismatch


# ============================================================================
# API Key Encryption Tests (6 essential tests from test_api_keys.py)
# ============================================================================

class TestAPIKeyEncryption:
    """Test API key encryption functionality."""

    def test_encrypt_api_key_produces_different_ciphertexts(self):
        """Test encrypting same API key twice produces different ciphertexts (with IV)."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            # Generate a valid Fernet key
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            api_key = "sk_test_1234567890abcdef"

            encrypted1 = encrypt_api_key(api_key)
            encrypted2 = encrypt_api_key(api_key)

            # Fernet includes timestamp, so encryptions will be different
            assert encrypted1 != encrypted2
            assert len(encrypted1) > len(api_key)
            assert len(encrypted2) > len(api_key)

    def test_encrypt_api_key_not_empty(self):
        """Test API key encryption produces non-empty result."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            api_key = "sk_test_key"
            encrypted = encrypt_api_key(api_key)

            assert encrypted is not None
            assert len(encrypted) > 0
            assert isinstance(encrypted, str)

    def test_encrypt_empty_api_key(self):
        """Test encrypting empty API key."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            encrypted = encrypt_api_key("")

            assert encrypted is not None
            assert len(encrypted) > 0

    def test_encrypt_api_key_with_special_characters(self):
        """Test encrypting API key with special characters."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            api_key = "key_with_!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
            encrypted = encrypt_api_key(api_key)

            assert encrypted is not None
            assert len(encrypted) > 0

    def test_encrypt_api_key_invalid_master_key(self):
        """Test encryption fails with invalid master key."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            mock_settings.encryption_master_key = "invalid_key"

            with pytest.raises(ValueError, match="Invalid encryption master key"):
                encrypt_api_key("sk_test_key")

    def test_fernet_key_validation(self):
        """Test _get_fernet validates encryption key format."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            # Invalid key format
            mock_settings.encryption_master_key = "not_base64_key"

            with pytest.raises(ValueError, match="Invalid encryption master key"):
                _get_fernet()


# ============================================================================
# API Key Decryption Tests (6 essential tests from test_api_keys.py)
# ============================================================================

class TestAPIKeyDecryption:
    """Test API key decryption functionality."""

    def test_decrypt_api_key_correct(self):
        """Test decryption of correctly encrypted API key."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            api_key = "sk_test_1234567890abcdef"
            encrypted = encrypt_api_key(api_key)
            decrypted = decrypt_api_key(encrypted)

            assert decrypted == api_key

    def test_decrypt_empty_encrypted_key(self):
        """Test decryption of empty string encrypted key."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            encrypted = encrypt_api_key("")
            decrypted = decrypt_api_key(encrypted)

            assert decrypted == ""

    def test_decrypt_with_wrong_key(self):
        """Test decryption fails with wrong master key."""
        # Encrypt with one key
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key1 = Fernet.generate_key()
            mock_settings.encryption_master_key = key1.decode()
            encrypted = encrypt_api_key("sk_test_key")

        # Try to decrypt with different key
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key2 = Fernet.generate_key()
            mock_settings.encryption_master_key = key2.decode()

            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_api_key(encrypted)

    def test_decrypt_invalid_ciphertext(self):
        """Test decryption fails with invalid ciphertext."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_api_key("invalid_ciphertext")

    def test_decrypt_corrupted_ciphertext(self):
        """Test decryption fails with corrupted ciphertext."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            # Create valid encrypted data then corrupt it
            encrypted = encrypt_api_key("sk_test_key")
            corrupted = encrypted[:-10] + "corrupted!"

            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_api_key(corrupted)

    def test_encrypt_decrypt_roundtrip(self):
        """Test encrypt-decrypt roundtrip preserves data."""
        with patch('app.core.utils.encryption.settings') as mock_settings:
            key = Fernet.generate_key()
            mock_settings.encryption_master_key = key.decode()

            test_keys = [
                "sk_test_simple",
                "sk_test_with_numbers_12345",
                "sk_test_special_!@#$%",
                "a" * 500,  # Long key
            ]

            for original_key in test_keys:
                encrypted = encrypt_api_key(original_key)
                decrypted = decrypt_api_key(encrypted)
                assert decrypted == original_key, f"Failed for key: {original_key}"


# ============================================================================
# API Key CRUD Tests (7 essential tests from test_api_keys.py)
# ============================================================================

class TestAPIKeyCRUD:
    """Test API key CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        """Test creating encrypted API key in database."""
        plain_value = "sk_test_1234567890"
        user_id = "user_123"
        service_id = "service_456"

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool), \
             patch('app.database.crud.api_keys.generate_id', return_value="key_abc123"), \
             patch('app.database.crud.api_keys.encrypt_api_key', return_value="encrypted_value"):

            key_id = await create_api_key(plain_value, user_id, service_id)

            assert key_id == "key_abc123"
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_key(self):
        """Test retrieving API key from database (encrypted)."""
        key_id = "key_123"
        expected_result = {
            "id": key_id,
            "encrypted_value": "encrypted_abc",
            "user_id": "user_123",
            "service_id": "service_456"
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=expected_result)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool):
            result = await get_api_key(key_id)

            assert result == expected_result
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_key_decrypted(self):
        """Test retrieving and decrypting API key."""
        key_id = "key_123"
        encrypted_value = "encrypted_abc"
        decrypted_value = "sk_test_1234567890"

        mock_row = {"encrypted_value": encrypted_value}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool), \
             patch('app.database.crud.api_keys.decrypt_api_key', return_value=decrypted_value):

            result = await get_api_key_decrypted(key_id)

            assert result == decrypted_value
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_api_keys_all(self):
        """Test listing all API keys."""
        expected_keys = [
            {"id": "key_1", "encrypted_value": "enc1", "user_id": "user_1"},
            {"id": "key_2", "encrypted_value": "enc2", "user_id": "user_2"},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=expected_keys)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool):
            result = await list_api_keys()

            assert len(result) == 2
            assert result == expected_keys
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_api_keys_by_user(self):
        """Test listing API keys filtered by user ID."""
        user_id = "user_123"
        expected_keys = [
            {"id": "key_1", "encrypted_value": "enc1", "user_id": user_id},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=expected_keys)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool):
            result = await list_api_keys(user_id=user_id)

            assert len(result) == 1
            assert result[0]["user_id"] == user_id
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_api_key(self):
        """Test updating (rotating) API key."""
        key_id = "key_123"
        new_plain_value = "sk_new_1234567890"

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool), \
             patch('app.database.crud.api_keys.encrypt_api_key', return_value="new_encrypted"):

            result = await update_api_key(key_id, new_plain_value)

            assert result is True
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_api_key(self):
        """Test deleting API key."""
        key_id = "key_123"

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

        with patch('app.database.crud.api_keys.get_pool', return_value=mock_pool):
            result = await delete_api_key(key_id)

            assert result is True
            mock_conn.execute.assert_called_once()
