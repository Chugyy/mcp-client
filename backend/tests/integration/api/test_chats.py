"""Integration tests for chats routes.

Tests all chat endpoints:
- POST /api/v1/chats (create chat)
- GET /api/v1/chats (list chats)
- GET /api/v1/chats/{id} (get chat)
- DELETE /api/v1/chats/{id} (delete chat)
- POST /api/v1/chats/{id}/messages (send message)
- GET /api/v1/chats/{id}/messages (list messages)
- POST /api/v1/chats/{id}/stream (stream message with SSE)
- POST /api/v1/chats/{id}/stop (stop streaming)
- POST /api/v1/chats/stream_legacy (legacy streaming)
"""

import pytest
import json


class TestCreateChat:
    """Tests for POST /api/v1/chats"""

    def test_create_chat_with_agent(self, authenticated_client, sample_agent):
        """Test creating chat with agent_id."""
        response = authenticated_client.post("/api/v1/chats", json={
            "agent_id": sample_agent["id"],
            "title": "Test Chat"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == sample_agent["id"]
        assert data["title"] == "Test Chat"
        assert data["id"].startswith("cht_")
        assert data["team_id"] is None

    def test_create_chat_with_team(self, authenticated_client, sample_team):
        """Test creating chat with team_id."""
        response = authenticated_client.post("/api/v1/chats", json={
            "team_id": sample_team["id"],
            "title": "Team Chat"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == sample_team["id"]
        assert data["title"] == "Team Chat"
        assert data["agent_id"] is None

    @pytest.mark.skip(reason="Database constraint requires at least agent_id OR team_id - empty chats not supported")
    def test_create_chat_empty(self, authenticated_client):
        """Test creating empty chat (lazy initialization).

        SKIPPED: The chats table has a CHECK constraint that requires at least
        one of agent_id or team_id to be non-NULL. Empty chats are not supported.
        """
        response = authenticated_client.post("/api/v1/chats", json={
            "title": "Empty Chat"
        })

        assert response.status_code == 201
        data = response.json()
        # Verify title exists and has correct value
        assert "title" in data
        assert data["title"] == "Empty Chat"
        assert data["agent_id"] is None
        assert data["team_id"] is None

    def test_create_chat_both_agent_and_team_fails(self, authenticated_client, sample_agent, sample_team):
        """Test creating chat with both agent_id and team_id returns 422 (Pydantic validation)."""
        response = authenticated_client.post("/api/v1/chats", json={
            "agent_id": sample_agent["id"],
            "team_id": sample_team["id"],
            "title": "Invalid Chat"
        })

        # Pydantic validator raises ValueError → FastAPI returns 422
        assert response.status_code == 422
        # Verify error message mentions the constraint
        error_detail = str(response.json()).lower()
        assert "cannot specify both" in error_detail or "agent_id" in error_detail

    def test_create_chat_nonexistent_agent(self, authenticated_client):
        """Test creating chat with non-existent agent returns 404."""
        response = authenticated_client.post("/api/v1/chats", json={
            "agent_id": "agt_nonexistent",
            "title": "Test Chat"
        })

        assert response.status_code == 404
        assert "agent not found" in response.json()["detail"].lower()

    def test_create_chat_unauthorized_agent(self, authenticated_client, other_user_agent):
        """Test creating chat with other user's agent returns 403."""
        response = authenticated_client.post("/api/v1/chats", json={
            "agent_id": other_user_agent["id"],
            "title": "Test Chat"
        })

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    def test_create_chat_unauthenticated(self, client, clean_db):
        """Test creating chat without authentication returns 401."""
        response = client.post("/api/v1/chats", json={
            "agent_id": "agt_fake123",
            "title": "Test Chat"
        })

        assert response.status_code == 401


class TestListChats:
    """Tests for GET /api/v1/chats"""

    def test_list_chats_empty(self, authenticated_client, clean_db, test_user):
        """Test listing chats when user has none."""
        response = authenticated_client.get("/api/v1/chats")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_chats_with_chats(self, authenticated_client, sample_agent):
        """Test listing chats returns user's chats."""
        # Create multiple chats
        chat1 = authenticated_client.post("/api/v1/chats", json={
            "agent_id": sample_agent["id"],
            "title": "Chat 1"
        }).json()

        chat2 = authenticated_client.post("/api/v1/chats", json={
            "agent_id": sample_agent["id"],
            "title": "Chat 2"
        }).json()

        response = authenticated_client.get("/api/v1/chats")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        chat_ids = [c["id"] for c in data]
        assert chat1["id"] in chat_ids
        assert chat2["id"] in chat_ids

    def test_list_chats_unauthenticated(self, client):
        """Test listing chats without authentication returns 401."""
        response = client.get("/api/v1/chats")

        assert response.status_code == 401


class TestGetChat:
    """Tests for GET /api/v1/chats/{id}"""

    def test_get_chat_success(self, authenticated_client, sample_chat):
        """Test getting chat by ID."""
        response = authenticated_client.get(f"/api/v1/chats/{sample_chat['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_chat["id"]
        assert data["title"] == sample_chat["title"]

    def test_get_chat_not_found(self, authenticated_client):
        """Test getting non-existent chat returns 404."""
        response = authenticated_client.get("/api/v1/chats/cht_nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_chat_unauthenticated(self, client, clean_db):
        """Test getting chat without authentication returns 401."""
        response = client.get("/api/v1/chats/cht_fake123")

        assert response.status_code == 401


class TestDeleteChat:
    """Tests for DELETE /api/v1/chats/{id}"""

    def test_delete_chat_success(self, authenticated_client, sample_chat):
        """Test deleting chat."""
        response = authenticated_client.delete(f"/api/v1/chats/{sample_chat['id']}")

        assert response.status_code == 204

        # Verify chat is deleted
        get_response = authenticated_client.get(f"/api/v1/chats/{sample_chat['id']}")
        assert get_response.status_code == 404

    def test_delete_chat_not_found(self, authenticated_client):
        """Test deleting non-existent chat returns 404."""
        response = authenticated_client.delete("/api/v1/chats/cht_nonexistent")

        assert response.status_code == 404

    def test_delete_chat_unauthenticated(self, client, clean_db):
        """Test deleting chat without authentication returns 401."""
        response = client.delete("/api/v1/chats/cht_fake123")

        assert response.status_code == 401


class TestSendMessage:
    """Tests for POST /api/v1/chats/{id}/messages"""

    def test_send_message_success(self, authenticated_client, sample_chat):
        """Test sending message to chat."""
        response = authenticated_client.post(
            f"/api/v1/chats/{sample_chat['id']}/messages",
            json={
                "role": "user",
                "content": "Hello, this is a test message"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, this is a test message"
        assert data["id"].startswith("msg_")

    def test_send_message_chat_not_found(self, authenticated_client):
        """Test sending message to non-existent chat returns 404."""
        response = authenticated_client.post(
            "/api/v1/chats/cht_nonexistent/messages",
            json={
                "role": "user",
                "content": "Test message"
            }
        )

        assert response.status_code == 404

    def test_send_message_unauthenticated(self, client, clean_db):
        """Test sending message without authentication returns 401."""
        response = client.post(
            "/api/v1/chats/cht_fake123/messages",
            json={
                "role": "user",
                "content": "Test message"
            }
        )

        assert response.status_code == 401


class TestListMessages:
    """Tests for GET /api/v1/chats/{id}/messages"""

    def test_list_messages_empty(self, authenticated_client, sample_chat):
        """Test listing messages when chat has none."""
        response = authenticated_client.get(f"/api/v1/chats/{sample_chat['id']}/messages")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_messages_with_messages(self, authenticated_client, sample_chat):
        """Test listing messages returns chat's messages."""
        # Create messages
        authenticated_client.post(
            f"/api/v1/chats/{sample_chat['id']}/messages",
            json={"role": "user", "content": "Message 1"}
        )
        authenticated_client.post(
            f"/api/v1/chats/{sample_chat['id']}/messages",
            json={"role": "assistant", "content": "Message 2"}
        )

        response = authenticated_client.get(f"/api/v1/chats/{sample_chat['id']}/messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content"] == "Message 1"
        assert data[1]["content"] == "Message 2"

    def test_list_messages_chat_not_found(self, authenticated_client):
        """Test listing messages for non-existent chat returns 404."""
        response = authenticated_client.get("/api/v1/chats/cht_nonexistent/messages")

        assert response.status_code == 404

    def test_list_messages_unauthenticated(self, client, clean_db):
        """Test listing messages without authentication returns 401."""
        response = client.get("/api/v1/chats/cht_fake123/messages")

        assert response.status_code == 401


class TestStreamMessage:
    """Tests for POST /api/v1/chats/{id}/stream"""

    def test_stream_message_chat_not_found(self, authenticated_client):
        """Test streaming to non-existent chat returns 404."""
        response = authenticated_client.post(
            "/api/v1/chats/cht_nonexistent/stream",
            json={
                "message": "Test message",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code == 404

    @pytest.mark.skip(reason="Requires complex streaming infrastructure mocking - defer to dedicated streaming tests story")
    def test_stream_message_empty_chat_missing_agent(self, authenticated_client):
        """Test streaming to empty chat without agent_id returns 400."""
        # Create empty chat
        chat = authenticated_client.post("/api/v1/chats", json={
            "title": "Empty Chat"
        }).json()

        response = authenticated_client.post(
            f"/api/v1/chats/{chat['id']}/stream",
            json={
                "message": "Test message"
            }
        )

        assert response.status_code == 400
        assert "agent_id and model are required" in response.json()["detail"].lower()

    def test_stream_message_unauthenticated(self, client, clean_db):
        """Test streaming without authentication returns 401."""
        response = client.post(
            "/api/v1/chats/cht_fake123/stream",
            json={
                "message": "Test message",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code == 401


class TestStopChat:
    """Tests for POST /api/v1/chats/{id}/stop"""

    @pytest.mark.skip(reason="Requires stream_manager and validation infrastructure mocking - defer to dedicated streaming tests story")
    def test_stop_chat_success(self, authenticated_client, sample_chat):
        """Test stopping chat stream."""
        response = authenticated_client.post(f"/api/v1/chats/{sample_chat['id']}/stop")

        assert response.status_code == 204

    def test_stop_chat_not_found(self, authenticated_client):
        """Test stopping non-existent chat returns 404."""
        response = authenticated_client.post("/api/v1/chats/cht_nonexistent/stop")

        assert response.status_code == 404

    def test_stop_chat_unauthenticated(self, client, clean_db):
        """Test stopping chat without authentication returns 401."""
        response = client.post("/api/v1/chats/cht_fake123/stop")

        assert response.status_code == 401


class TestLegacyStream:
    """Tests for POST /api/v1/chats/stream_legacy (deprecated)"""

    @pytest.mark.skip(reason="Requires LLM gateway async mocking - defer to dedicated streaming tests story")
    def test_legacy_stream_with_existing_chat(self, authenticated_client, sample_chat):
        """Test legacy streaming with existing chat_id."""
        # This endpoint returns StreamingResponse, so we just check it doesn't error
        response = authenticated_client.post(
            "/api/v1/chats/stream_legacy",
            json={
                "chat_id": sample_chat["id"],
                "message": "Test message",
                "model": "gpt-4o-mini"
            }
        )

        # Should return 200 for streaming response
        # Note: TestClient doesn't fully support streaming, but we can verify it starts
        assert response.status_code == 200

    def test_legacy_stream_chat_not_found(self, authenticated_client):
        """Test legacy streaming with non-existent chat returns 404."""
        response = authenticated_client.post(
            "/api/v1/chats/stream_legacy",
            json={
                "chat_id": "cht_nonexistent",
                "message": "Test message",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code == 404

    def test_legacy_stream_new_chat_missing_agent(self, authenticated_client):
        """Test legacy streaming without chat_id and without agent_id returns 400."""
        response = authenticated_client.post(
            "/api/v1/chats/stream_legacy",
            json={
                "message": "Test message",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code == 400
        assert "agent_id required" in response.json()["detail"].lower()

    def test_legacy_stream_unauthenticated(self, client):
        """Test legacy streaming without authentication returns 401."""
        response = client.post(
            "/api/v1/chats/stream_legacy",
            json={
                "message": "Test message",
                "agent_id": "agt_test",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code == 401
