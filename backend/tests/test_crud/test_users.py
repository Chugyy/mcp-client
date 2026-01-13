"""Integration tests for users CRUD module."""

import pytest
import json
from app.database.crud import users
from app.core.utils.auth import hash_password


@pytest.mark.asyncio
async def test_create_user_success(clean_db, mock_pool_for_crud):
    """Test creating user with valid data."""
    hashed_pw = hash_password("securepassword123")
    user_id = await users.create_user(
        email="newuser@example.com",
        password=hashed_pw,
        name="New User"
    )

    # Verify user was created
    assert user_id is not None
    assert isinstance(user_id, str)
    assert user_id.startswith("usr_")

    # Fetch and verify user data
    user = await users.get_user(user_id)
    assert user["email"] == "newuser@example.com"
    assert user["name"] == "New User"
    assert user["id"] == user_id
    assert user["password"] == hashed_pw


@pytest.mark.asyncio
async def test_create_user_duplicate_email(clean_db, sample_user, mock_pool_for_crud):
    """Test creating user with duplicate email causes database constraint violation."""
    hashed_pw = hash_password("password123")

    # Attempt to create duplicate - should raise exception from database
    with pytest.raises(Exception) as exc_info:
        await users.create_user(
            email=sample_user["email"],  # Duplicate email
            password=hashed_pw,
            name="Duplicate User"
        )

    # Verify it's a unique violation error
    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_user_by_id(clean_db, sample_user, mock_pool_for_crud):
    """Test getting user by ID."""
    user = await users.get_user(sample_user["id"])

    assert user is not None
    assert user["id"] == sample_user["id"]
    assert user["email"] == sample_user["email"]
    assert user["name"] == sample_user["name"]


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(clean_db, mock_pool_for_crud):
    """Test getting non-existent user returns None."""
    user = await users.get_user("usr_nonexistent123")
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email(clean_db, sample_user, mock_pool_for_crud):
    """Test getting user by email."""
    user = await users.get_user_by_email(sample_user["email"])

    assert user is not None
    assert user["id"] == sample_user["id"]
    assert user["email"] == sample_user["email"]


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(clean_db, mock_pool_for_crud):
    """Test getting user by non-existent email returns None."""
    user = await users.get_user_by_email("nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_update_user_success(clean_db, sample_user, mock_pool_for_crud):
    """Test updating user data."""
    success = await users.update_user(
        sample_user["id"],
        name="Updated Name"
    )
    assert success is True

    # Verify update
    user = await users.get_user(sample_user["id"])
    assert user["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_preferences(clean_db, sample_user, mock_pool_for_crud):
    """Test updating user preferences."""
    new_prefs = {"theme": "dark", "language": "en"}
    success = await users.update_user(
        sample_user["id"],
        preferences=new_prefs
    )
    assert success is True

    # Verify update
    user = await users.get_user(sample_user["id"])
    # Parse preferences from JSON string if needed
    prefs = user["preferences"]
    if isinstance(prefs, str):
        prefs = json.loads(prefs)
    assert prefs["theme"] == "dark"
    assert prefs["language"] == "en"


@pytest.mark.asyncio
async def test_update_user_password(clean_db, sample_user, mock_pool_for_crud):
    """Test updating user password."""
    new_password = hash_password("newpassword456")
    success = await users.update_user_password(
        sample_user["id"],
        new_password
    )
    assert success is True

    # Verify password was updated
    user = await users.get_user(sample_user["id"])
    assert user["password"] == new_password


@pytest.mark.asyncio
async def test_delete_user_success(clean_db, sample_user, mock_pool_for_crud):
    """Test deleting user."""
    success = await users.delete_user(sample_user["id"])
    assert success is True

    # Verify deletion
    user = await users.get_user(sample_user["id"])
    assert user is None


@pytest.mark.asyncio
async def test_delete_user_not_found(clean_db, mock_pool_for_crud):
    """Test deleting non-existent user returns False."""
    success = await users.delete_user("usr_nonexistent123")
    assert success is False


@pytest.mark.asyncio
async def test_list_users(clean_db, sample_user, mock_pool_for_crud):
    """Test listing users."""
    users_list = await users.list_users()

    assert isinstance(users_list, list)
    assert len(users_list) >= 1
    assert any(u["id"] == sample_user["id"] for u in users_list)


@pytest.mark.asyncio
async def test_list_users_multiple(clean_db, mock_pool_for_crud):
    """Test listing multiple users."""
    # Create multiple users
    hashed_pw = hash_password("password123")
    user1_id = await users.create_user(
        email="user1@example.com",
        password=hashed_pw,
        name="User 1"
    )
    user2_id = await users.create_user(
        email="user2@example.com",
        password=hashed_pw,
        name="User 2"
    )

    users_list = await users.list_users()

    assert len(users_list) >= 2
    assert any(u["id"] == user1_id for u in users_list)
    assert any(u["id"] == user2_id for u in users_list)
    # Verify ordering (most recent first)
    assert users_list[0]["id"] == user2_id  # Created last, should be first
