"""Integration tests for chats CRUD module."""

import pytest
from app.database.crud import chats



@pytest.fixture
async def sample_chat(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Create a sample chat for testing."""
    chat_id = await chats.create_chat(
        user_id=sample_user["id"],
        title="Test Chat",
        agent_id=sample_agent["id"]
    )
    chat = await chats.get_chat(chat_id)
    return chat


@pytest.mark.asyncio
async def test_create_chat_session(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test creating a chat session."""
    chat_id = await chats.create_chat(
        user_id=sample_user["id"],
        title="New Chat Session",
        agent_id=sample_agent["id"]
    )

    # Verify chat was created
    assert chat_id is not None
    assert isinstance(chat_id, str)
    assert chat_id.startswith("cht_")

    # Fetch and verify chat data
    chat = await chats.get_chat(chat_id)
    assert chat["title"] == "New Chat Session"
    assert chat["user_id"] == sample_user["id"]
    assert chat["agent_id"] == sample_agent["id"]


@pytest.mark.asyncio
async def test_add_message_to_chat(clean_db, sample_chat, mock_pool_for_crud):
    """Test adding a message to a chat."""
    message_id = await chats.create_message(
        chat_id=sample_chat["id"],
        role="user",
        content="Hello, this is a test message"
    )

    # Verify message was created
    assert message_id is not None
    assert isinstance(message_id, str)
    assert message_id.startswith("msg_")

    # Get messages and verify
    messages = await chats.get_messages_by_chat(sample_chat["id"])
    assert len(messages) >= 1
    assert any(m["id"] == message_id for m in messages)
    assert messages[0]["content"] == "Hello, this is a test message"
    assert messages[0]["role"] == "user"


@pytest.mark.asyncio
async def test_get_chat_with_messages(clean_db, sample_chat, mock_pool_for_crud):
    """Test getting a chat with its messages."""
    # Add multiple messages
    msg1_id = await chats.create_message(
        chat_id=sample_chat["id"],
        role="user",
        content="First message"
    )
    msg2_id = await chats.create_message(
        chat_id=sample_chat["id"],
        role="assistant",
        content="Second message"
    )

    # Get chat
    chat = await chats.get_chat(sample_chat["id"])
    assert chat is not None

    # Get messages
    messages = await chats.get_messages_by_chat(sample_chat["id"])
    assert len(messages) >= 2
    assert any(m["id"] == msg1_id for m in messages)
    assert any(m["id"] == msg2_id for m in messages)


@pytest.mark.asyncio
async def test_update_chat_metadata(clean_db, sample_chat, mock_pool_for_crud):
    """Test updating chat metadata (title)."""
    success = await chats.update_chat_title(
        sample_chat["id"],
        "Updated Chat Title"
    )
    assert success is True

    # Verify update
    chat = await chats.get_chat(sample_chat["id"])
    assert chat["title"] == "Updated Chat Title"


@pytest.mark.asyncio
async def test_delete_chat_cascade_messages(clean_db, sample_chat, mock_pool_for_crud):
    """Test deleting a chat cascades to messages."""
    # Add messages to the chat
    await chats.create_message(
        chat_id=sample_chat["id"],
        role="user",
        content="Message 1"
    )
    await chats.create_message(
        chat_id=sample_chat["id"],
        role="assistant",
        content="Message 2"
    )

    # Verify messages exist
    messages_before = await chats.get_messages_by_chat(sample_chat["id"])
    assert len(messages_before) >= 2

    # Delete chat
    success = await chats.delete_chat(sample_chat["id"])
    assert success is True

    # Verify chat is deleted
    chat = await chats.get_chat(sample_chat["id"])
    assert chat is None

    # Verify messages are also deleted (cascade)
    messages_after = await chats.get_messages_by_chat(sample_chat["id"])
    assert len(messages_after) == 0


@pytest.mark.asyncio
async def test_list_chats_with_pagination(clean_db, sample_user, sample_agent, mock_pool_for_crud):
    """Test listing chats with pagination."""
    # Create multiple chats
    chat1_id = await chats.create_chat(
        user_id=sample_user["id"],
        title="Chat 1",
        agent_id=sample_agent["id"]
    )
    chat2_id = await chats.create_chat(
        user_id=sample_user["id"],
        title="Chat 2",
        agent_id=sample_agent["id"]
    )

    # List all chats for user
    user_chats = await chats.list_chats_by_user(sample_user["id"])

    assert len(user_chats) >= 2
    assert any(c["id"] == chat1_id for c in user_chats)
    assert any(c["id"] == chat2_id for c in user_chats)
    # Verify ordering (most recently updated first)
    assert user_chats[0]["id"] == chat2_id  # Created last, should be first


@pytest.mark.asyncio
async def test_create_message_with_metadata(clean_db, sample_chat, mock_pool_for_crud):
    """Test creating a message with metadata."""
    import json
    metadata = {"tool_calls": ["search"], "tokens": 100}
    message_id = await chats.create_message(
        chat_id=sample_chat["id"],
        role="assistant",
        content="Response with metadata",
        metadata=metadata
    )

    # Get messages and verify metadata
    messages = await chats.get_messages_by_chat(sample_chat["id"])
    message = next(m for m in messages if m["id"] == message_id)
    # Handle case where metadata might be returned as JSON string
    actual_metadata = message["metadata"] if isinstance(message["metadata"], dict) else json.loads(message["metadata"])
    assert actual_metadata == metadata


@pytest.mark.asyncio
async def test_get_chat_not_found(clean_db, mock_pool_for_crud):
    """Test getting non-existent chat returns None."""
    chat = await chats.get_chat("cht_nonexistent123")
    assert chat is None


@pytest.mark.asyncio
async def test_delete_chat_not_found(clean_db, mock_pool_for_crud):
    """Test deleting non-existent chat returns False."""
    success = await chats.delete_chat("cht_nonexistent123")
    assert success is False
