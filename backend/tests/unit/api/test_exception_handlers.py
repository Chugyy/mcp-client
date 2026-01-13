"""Unit tests for global exception handler.

Tests verify that all custom exceptions are correctly mapped to HTTP status codes
and that error responses follow the expected format.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.v1.exception_handlers import app_exception_handler
from app.core.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    ConflictError,
    QuotaExceededError,
    RateLimitError,
    CircuitBreakerOpenError
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    return request


# ============================================================================
# HTTP Status Code Mapping Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validation_error_returns_400(mock_request):
    """ValidationError should map to 400 Bad Request."""
    exc = ValidationError("Invalid input data")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["detail"] == "Invalid input data"
    assert body["type"] == "ValidationError"


@pytest.mark.asyncio
async def test_authentication_error_returns_401(mock_request):
    """AuthenticationError should map to 401 Unauthorized."""
    exc = AuthenticationError("Invalid credentials")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 401
    body = json.loads(response.body)
    assert body["detail"] == "Invalid credentials"
    assert body["type"] == "AuthenticationError"


@pytest.mark.asyncio
async def test_permission_error_returns_403(mock_request):
    """PermissionError should map to 403 Forbidden."""
    exc = PermissionError("Access denied")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 403
    body = json.loads(response.body)
    assert body["detail"] == "Access denied"
    assert body["type"] == "PermissionError"


@pytest.mark.asyncio
async def test_not_found_error_returns_404(mock_request):
    """NotFoundError should map to 404 Not Found."""
    exc = NotFoundError("Resource not found")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["detail"] == "Resource not found"
    assert body["type"] == "NotFoundError"


@pytest.mark.asyncio
async def test_conflict_error_returns_409(mock_request):
    """ConflictError should map to 409 Conflict."""
    exc = ConflictError("Resource already exists")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 409
    body = json.loads(response.body)
    assert body["detail"] == "Resource already exists"
    assert body["type"] == "ConflictError"


@pytest.mark.asyncio
async def test_quota_exceeded_error_returns_429(mock_request):
    """QuotaExceededError should map to 429 Too Many Requests."""
    exc = QuotaExceededError("API quota exceeded")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 429
    body = json.loads(response.body)
    assert body["detail"] == "API quota exceeded"
    assert body["type"] == "QuotaExceededError"


@pytest.mark.asyncio
async def test_rate_limit_error_returns_429(mock_request):
    """RateLimitError should map to 429 Too Many Requests."""
    exc = RateLimitError("Rate limit exceeded")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 429
    body = json.loads(response.body)
    assert body["detail"] == "Rate limit exceeded"
    assert body["type"] == "RateLimitError"


@pytest.mark.asyncio
async def test_circuit_breaker_open_error_returns_503(mock_request):
    """CircuitBreakerOpenError should map to 503 Service Unavailable."""
    exc = CircuitBreakerOpenError("Service temporarily unavailable")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["detail"] == "Service temporarily unavailable"
    assert body["type"] == "CircuitBreakerOpenError"


@pytest.mark.asyncio
async def test_generic_app_exception_returns_500(mock_request):
    """Generic AppException should map to 500 Internal Server Error."""
    exc = AppException("Unexpected error occurred")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["detail"] == "Unexpected error occurred"
    assert body["type"] == "AppException"


# ============================================================================
# Response Format Tests
# ============================================================================

@pytest.mark.asyncio
async def test_response_includes_detail_field(mock_request):
    """Response should always include 'detail' field."""
    exc = NotFoundError("Test message")

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert "detail" in body
    assert body["detail"] == "Test message"


@pytest.mark.asyncio
async def test_response_includes_type_field(mock_request):
    """Response should always include 'type' field with exception class name."""
    exc = ValidationError("Test message")

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert "type" in body
    assert body["type"] == "ValidationError"


@pytest.mark.asyncio
async def test_exception_details_preserved_in_response(mock_request):
    """Additional details should be merged into response."""
    exc = ValidationError(
        "Validation failed",
        details={
            "field": "email",
            "constraint": "format",
            "provided_value": "invalid-email"
        }
    )

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Validation failed"
    assert body["type"] == "ValidationError"
    assert body["field"] == "email"
    assert body["constraint"] == "format"
    assert body["provided_value"] == "invalid-email"


@pytest.mark.asyncio
async def test_exception_without_details_works(mock_request):
    """Exception without details should work correctly."""
    exc = NotFoundError("Resource not found")

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Resource not found"
    assert body["type"] == "NotFoundError"
    # Should only have detail and type, no extra fields
    assert len(body) == 2


@pytest.mark.asyncio
async def test_empty_details_dict_handled_correctly(mock_request):
    """Empty details dict should not add extra fields."""
    exc = NotFoundError("Resource not found", details={})

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Resource not found"
    assert body["type"] == "NotFoundError"
    assert len(body) == 2


# ============================================================================
# Response Type Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handler_returns_json_response(mock_request):
    """Handler should return a JSONResponse instance."""
    exc = NotFoundError("Test")

    response = await app_exception_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)


@pytest.mark.asyncio
async def test_response_content_type_is_json(mock_request):
    """Response should have JSON content type."""
    exc = NotFoundError("Test")

    response = await app_exception_handler(mock_request, exc)

    # JSONResponse sets media_type
    assert response.media_type == "application/json"


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_exception_with_special_characters_in_message(mock_request):
    """Exception message with special characters should be handled."""
    exc = ValidationError("Invalid format: expected 'user@example.com'")

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Invalid format: expected 'user@example.com'"


@pytest.mark.asyncio
async def test_exception_with_unicode_message(mock_request):
    """Exception message with unicode characters should be handled."""
    exc = NotFoundError("Usuario no encontrado ñáéíóú")

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Usuario no encontrado ñáéíóú"


@pytest.mark.asyncio
async def test_exception_with_nested_details(mock_request):
    """Exception with nested details dict should be serialized."""
    exc = ValidationError(
        "Validation failed",
        details={
            "errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "password", "message": "Too short"}
            ]
        }
    )

    response = await app_exception_handler(mock_request, exc)

    body = json.loads(response.body)
    assert body["detail"] == "Validation failed"
    assert "errors" in body
    assert len(body["errors"]) == 2
    assert body["errors"][0]["field"] == "email"


# ============================================================================
# Request Context Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handler_works_with_different_request_paths(mock_request):
    """Handler should work regardless of request path."""
    mock_request.url.path = "/api/v1/users/123"
    exc = NotFoundError("User not found")

    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_handler_works_with_different_http_methods(mock_request):
    """Handler should work with any HTTP method."""
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        mock_request.method = method
        exc = NotFoundError("Test")

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 404


# ============================================================================
# Integration Tests (with actual Request object)
# ============================================================================

@pytest.mark.asyncio
async def test_handler_with_real_request_object():
    """Test handler with a more realistic Request mock."""
    from starlette.datastructures import URL

    request = Mock(spec=Request)
    request.url = URL("http://localhost/api/v1/test")
    request.method = "GET"

    exc = ValidationError("Test validation error")

    response = await app_exception_handler(request, exc)

    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["detail"] == "Test validation error"
    assert body["type"] == "ValidationError"
