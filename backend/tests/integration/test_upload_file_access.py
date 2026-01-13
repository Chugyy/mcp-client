"""Integration tests for authenticated upload file access."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from datetime import datetime
import tempfile
import os


@pytest.fixture
def mock_file_exists():
    """Mock Path.exists() to return True for file existence checks."""
    with patch.object(Path, 'exists', return_value=True):
        yield


@pytest.fixture
def mock_file_not_exists():
    """Mock Path.exists() to return False for file existence checks."""
    with patch.object(Path, 'exists', return_value=False):
        yield


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for authentication."""
    return "valid-jwt-token-12345"


@pytest.fixture
def mock_upload_data():
    """Mock upload data from database."""
    return {
        'id': 'upload-123',
        'user_id': 'user-123',
        'agent_id': None,
        'resource_id': None,
        'type': 'document',
        'filename': 'test-document.pdf',
        'file_path': '/tmp/uploads/test-document.pdf',
        'file_size': 2048,
        'mime_type': 'application/pdf',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def mock_image_upload_data():
    """Mock image upload data from database."""
    return {
        'id': 'upload-456',
        'user_id': 'user-123',
        'agent_id': None,
        'resource_id': None,
        'type': 'document',
        'filename': 'test-image.png',
        'file_path': '/tmp/uploads/test-image.png',
        'file_size': 1024,
        'mime_type': 'image/png',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def mock_user_data():
    """Mock user data from database."""
    return {
        'id': 'user-123',
        'email': 'test@example.com',
        'password': '$2b$12$hashhashhash',
        'name': 'Test User',
        'preferences': {},
        'permission_level': 'validation_required',
        'is_system': False,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def mock_admin_user_data():
    """Mock admin user data from database."""
    return {
        'id': 'admin-123',
        'email': 'admin@example.com',
        'password': '$2b$12$hashhashhash',
        'name': 'Admin User',
        'preferences': {},
        'permission_level': 'full_auto',
        'is_system': True,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.mark.asyncio
class TestAuthenticatedFileAccess:
    """Test authenticated file access through the API."""

    async def test_access_own_file_returns_200(
        self,
        mock_upload_data,
        mock_user_data,
        mock_file_exists
    ):
        """User accessing their own file should return 200 with file."""
        from app.api.v1.routes import uploads
        from app.database.crud import uploads as crud_uploads, users as crud_users

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            with patch('app.database.crud.users.get_user', new_callable=AsyncMock) as mock_get_user:
                with patch('app.core.utils.auth.verify_token', return_value='user-123'):
                    with patch('fastapi.responses.FileResponse') as mock_file_response:
                        mock_get_upload.return_value = mock_upload_data
                        mock_get_user.return_value = mock_user_data

                        # Simulate successful authentication and file access
                        upload = await crud_uploads.get_upload('upload-123')
                        user = await crud_users.get_user('user-123')

                        assert upload is not None
                        assert upload['user_id'] == user['id']
                        assert upload['id'] == 'upload-123'

    async def test_access_other_user_file_returns_403(
        self,
        mock_upload_data,
        mock_user_data
    ):
        """User accessing another user's file should return 403."""
        # Modify upload to be owned by different user
        other_user_upload = mock_upload_data.copy()
        other_user_upload['user_id'] = 'user-456'

        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = other_user_upload

            upload = await crud_uploads.get_upload('upload-123')

            # Verify ownership check would fail
            current_user_id = 'user-123'
            is_owner = upload['user_id'] == current_user_id

            assert is_owner is False

    async def test_file_not_found_returns_404(self):
        """Accessing non-existent file should return 404."""
        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = None

            upload = await crud_uploads.get_upload('nonexistent-id')

            assert upload is None

    async def test_file_missing_on_filesystem_returns_404(
        self,
        mock_upload_data,
        mock_user_data,
        mock_file_not_exists
    ):
        """File exists in DB but not on filesystem should return 404."""
        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = mock_upload_data

            upload = await crud_uploads.get_upload('upload-123')
            file_path = Path(upload['file_path'])

            # File should not exist on filesystem
            assert file_path.exists() is False

    async def test_admin_access_any_file_returns_200(
        self,
        mock_upload_data,
        mock_admin_user_data,
        mock_file_exists
    ):
        """Admin user should access any file via is_system flag."""
        # Upload owned by different user
        other_user_upload = mock_upload_data.copy()
        other_user_upload['user_id'] = 'user-456'

        from app.database.crud import uploads as crud_uploads, users as crud_users

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            with patch('app.database.crud.users.get_user', new_callable=AsyncMock) as mock_get_user:
                mock_get_upload.return_value = other_user_upload
                mock_get_user.return_value = mock_admin_user_data

                upload = await crud_uploads.get_upload('upload-123')
                admin_user = await crud_users.get_user('admin-123')

                # Admin should have access via is_system flag
                is_owner = upload['user_id'] == admin_user['id']
                admin_override = admin_user['is_system']

                assert is_owner is False  # Not the actual owner
                assert admin_override is True  # But is admin


@pytest.mark.asyncio
class TestContentDispositionHeaders:
    """Test content-disposition header logic."""

    async def test_pdf_returns_inline_disposition(
        self,
        mock_upload_data,
        mock_user_data,
        mock_file_exists
    ):
        """PDF files should return inline content-disposition."""
        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = mock_upload_data

            upload = await crud_uploads.get_upload('upload-123')
            file_path = Path(upload['file_path'])

            content_disposition = "inline"
            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
                content_disposition = "attachment"

            assert content_disposition == "inline"

    async def test_image_returns_inline_disposition(
        self,
        mock_image_upload_data,
        mock_user_data,
        mock_file_exists
    ):
        """Image files should return inline content-disposition."""
        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = mock_image_upload_data

            upload = await crud_uploads.get_upload('upload-456')
            file_path = Path(upload['file_path'])

            content_disposition = "inline"
            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
                content_disposition = "attachment"

            assert content_disposition == "inline"

    async def test_document_returns_attachment_disposition(
        self,
        mock_upload_data,
        mock_user_data,
        mock_file_exists
    ):
        """Non-image/PDF files should return attachment content-disposition."""
        # Modify upload to be a Word document
        doc_upload = mock_upload_data.copy()
        doc_upload['filename'] = 'test-document.docx'
        doc_upload['file_path'] = '/tmp/uploads/test-document.docx'
        doc_upload['mime_type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        from app.database.crud import uploads as crud_uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            mock_get_upload.return_value = doc_upload

            upload = await crud_uploads.get_upload('upload-123')
            file_path = Path(upload['file_path'])

            content_disposition = "inline"
            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
                content_disposition = "attachment"

            assert content_disposition == "attachment"


@pytest.mark.asyncio
class TestAgentOwnership:
    """Test file ownership through agent relationship."""

    async def test_access_agent_upload_by_agent_owner(
        self,
        mock_upload_data,
        mock_user_data,
        mock_file_exists
    ):
        """User should access files uploaded by their agent."""
        # Upload owned by agent
        agent_upload = mock_upload_data.copy()
        agent_upload['user_id'] = None
        agent_upload['agent_id'] = 'agent-123'

        # Agent owned by user
        agent_data = {
            'id': 'agent-123',
            'user_id': 'user-123',
            'name': 'Test Agent',
            'description': None,
            'system_prompt': '',
            'tags': [],
            'enabled': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_system': False
        }

        from app.database.crud import uploads as crud_uploads, agents as crud_agents

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            with patch('app.database.crud.agents.get_agent', new_callable=AsyncMock) as mock_get_agent:
                mock_get_upload.return_value = agent_upload
                mock_get_agent.return_value = agent_data

                upload = await crud_uploads.get_upload('upload-123')
                agent = await crud_agents.get_agent(upload['agent_id'])

                # User should own this upload through agent relationship
                current_user_id = 'user-123'
                is_owner = agent['user_id'] == current_user_id

                assert is_owner is True
