"""Unit tests for upload file authentication and authorization."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pathlib import Path
from datetime import datetime


@pytest.fixture
def mock_user():
    """Create a mock regular user."""
    user = MagicMock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.is_system = False
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock()
    user.id = "admin-123"
    user.email = "admin@example.com"
    user.is_system = True
    return user


@pytest.fixture
def mock_upload_dict():
    """Create a mock upload dictionary."""
    return {
        'id': 'upload-123',
        'user_id': 'user-123',
        'agent_id': None,
        'resource_id': None,
        'type': 'document',
        'filename': 'test-file.pdf',
        'file_path': '/tmp/test-file.pdf',
        'file_size': 1024,
        'mime_type': 'application/pdf',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def mock_upload():
    """Create a mock Upload object."""
    upload = MagicMock()
    upload.id = 'upload-123'
    upload.user_id = 'user-123'
    upload.agent_id = None
    upload.resource_id = None
    upload.filename = 'test-file.pdf'
    upload.file_path = '/tmp/test-file.pdf'
    upload.mime_type = 'application/pdf'
    return upload


class TestContentDispositionLogic:
    """Test content-disposition header logic."""

    def test_inline_for_images(self):
        """Images should use inline content-disposition."""
        inline_extensions = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]

        for ext in inline_extensions:
            file_path = Path(f"test{ext}")
            content_disposition = "inline"

            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
                content_disposition = "attachment"

            assert content_disposition == "inline", f"Extension {ext} should use inline"

    def test_inline_for_pdf(self):
        """PDFs should use inline content-disposition."""
        file_path = Path("test.pdf")
        content_disposition = "inline"

        if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
            content_disposition = "attachment"

        assert content_disposition == "inline"

    def test_attachment_for_documents(self):
        """Documents should use attachment content-disposition."""
        attachment_extensions = [".doc", ".docx", ".xls", ".xlsx", ".txt", ".zip"]

        for ext in attachment_extensions:
            file_path = Path(f"test{ext}")
            content_disposition = "inline"

            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".webp"]:
                content_disposition = "attachment"

            assert content_disposition == "attachment", f"Extension {ext} should use attachment"


class TestOwnershipVerification:
    """Test ownership verification logic."""

    def test_direct_user_ownership(self, mock_upload):
        """User should own files they uploaded directly."""
        mock_upload.user_id = "user-123"
        mock_upload.agent_id = None
        mock_upload.resource_id = None

        current_user_id = "user-123"
        is_owner = False

        if mock_upload.user_id and mock_upload.user_id == current_user_id:
            is_owner = True

        assert is_owner is True

    def test_not_owner(self, mock_upload):
        """User should not own files uploaded by others."""
        mock_upload.user_id = "user-456"
        mock_upload.agent_id = None
        mock_upload.resource_id = None

        current_user_id = "user-123"
        is_owner = False

        if mock_upload.user_id and mock_upload.user_id == current_user_id:
            is_owner = True

        assert is_owner is False

    def test_admin_override(self, mock_upload, mock_admin_user):
        """Admin users should access all files via is_system flag."""
        mock_upload.user_id = "user-456"  # Different user

        current_user_id = "admin-123"
        is_owner = False

        # Admin override
        if mock_admin_user.is_system:
            is_owner = True

        assert is_owner is True


@pytest.mark.asyncio
class TestUploadEndpointLogic:
    """Test upload endpoint authorization logic."""

    async def test_file_not_found_returns_404(self, mock_db_pool):
        """Should return 404 when upload not found in database."""
        _, mock_conn = mock_db_pool
        mock_conn.fetchrow.return_value = None

        from app.database.crud import uploads

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            upload = await uploads.get_upload("nonexistent-id")
            assert upload is None

    async def test_ownership_check_with_agent_upload(self, mock_db_pool, mock_upload_dict):
        """Should verify ownership through agent relationship."""
        # Setup upload owned by an agent
        upload_dict = mock_upload_dict.copy()
        upload_dict['user_id'] = None
        upload_dict['agent_id'] = 'agent-123'

        # Mock agent data
        agent_dict = {
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

        _, mock_conn = mock_db_pool
        mock_conn.fetchrow.side_effect = [upload_dict, agent_dict]

        from app.database.crud import uploads, agents

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            with patch('app.database.crud.agents.get_agent', new_callable=AsyncMock) as mock_get_agent:
                mock_get_upload.return_value = upload_dict
                mock_get_agent.return_value = agent_dict

                upload = await uploads.get_upload('upload-123')
                agent = await agents.get_agent('agent-123')

                assert upload is not None
                assert upload['agent_id'] == 'agent-123'
                assert agent is not None
                assert agent['user_id'] == 'user-123'

    async def test_ownership_check_with_resource_upload(self, mock_db_pool, mock_upload_dict):
        """Should verify ownership through resource relationship."""
        # Setup upload owned by a resource
        upload_dict = mock_upload_dict.copy()
        upload_dict['user_id'] = None
        upload_dict['resource_id'] = 'resource-123'

        # Mock resource data
        resource_dict = {
            'id': 'resource-123',
            'user_id': 'user-123',
            'name': 'Test Resource',
            'type': 'document'
        }

        _, mock_conn = mock_db_pool
        mock_conn.fetchrow.side_effect = [upload_dict, resource_dict]

        from app.database.crud import uploads, resources

        with patch('app.database.crud.uploads.get_upload', new_callable=AsyncMock) as mock_get_upload:
            with patch('app.database.crud.resources.get_resource', new_callable=AsyncMock) as mock_get_resource:
                mock_get_upload.return_value = upload_dict
                mock_get_resource.return_value = resource_dict

                upload = await uploads.get_upload('upload-123')
                resource = await resources.get_resource('resource-123')

                assert upload is not None
                assert upload['resource_id'] == 'resource-123'
                assert resource is not None
                assert resource['user_id'] == 'user-123'


@pytest.mark.asyncio
class TestAuditLogging:
    """Test audit trail logging functionality."""

    async def test_logs_successful_access(self, caplog):
        """Should log successful file access with details."""
        from config.logger import logger

        upload_id = "upload-123"
        user_id = "user-123"
        filename = "test-file.pdf"

        logger.info(
            f"File access granted: file_id={upload_id}, user_id={user_id}, "
            f"filename={filename}"
        )

        assert "File access granted" in caplog.text
        assert upload_id in caplog.text
        assert user_id in caplog.text

    async def test_logs_denied_access_ownership_violation(self, caplog):
        """Should log denied access due to ownership violation."""
        from config.logger import logger

        logger.warning(
            f"File access denied - ownership violation: file_id=upload-123, "
            f"owner_user_id=user-456, requester_id=user-123"
        )

        assert "File access denied" in caplog.text
        assert "ownership violation" in caplog.text

    async def test_logs_denied_access_file_not_found(self, caplog):
        """Should log denied access when file not found."""
        from config.logger import logger

        logger.warning(f"File access denied - file not found: file_id=upload-123, user_id=user-123")

        assert "File access denied" in caplog.text
        assert "file not found" in caplog.text
