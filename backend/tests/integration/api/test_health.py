"""Integration tests for Health endpoints.

Tests cover:
- Basic health check endpoint
- Circuit breaker status endpoint (validates Story 1.1 Circuit Breaker Pattern)
- Healthy vs degraded system states
"""

import pytest
from unittest.mock import MagicMock, patch


def test_health_check_success(client):
    """Test GET /health returns healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


def test_circuit_breakers_all_closed(client):
    """Test GET /health/circuit-breakers when all circuits are closed (healthy)."""
    # Mock circuit breakers with all CLOSED state
    mock_circuit_breakers = {
        "openai": MagicMock(get_state=MagicMock(return_value={"state": "closed", "failure_count": 0})),
        "anthropic": MagicMock(get_state=MagicMock(return_value={"state": "closed", "failure_count": 0}))
    }

    with patch("app.core.services.llm.gateway.llm_gateway.circuit_breakers", mock_circuit_breakers):
        response = client.get("/health/circuit-breakers")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "circuit_breakers" in data
    assert data["circuit_breakers"]["openai"]["state"] == "closed"
    assert data["circuit_breakers"]["anthropic"]["state"] == "closed"


def test_circuit_breakers_one_open_returns_degraded(client):
    """Test GET /health/circuit-breakers when one circuit is open (degraded).

    This validates Story 1.1 Circuit Breaker Pattern behavior.
    """
    # Mock circuit breakers with one OPEN state
    mock_circuit_breakers = {
        "openai": MagicMock(get_state=MagicMock(return_value={"state": "open", "failure_count": 5})),
        "anthropic": MagicMock(get_state=MagicMock(return_value={"state": "closed", "failure_count": 0}))
    }

    with patch("app.core.services.llm.gateway.llm_gateway.circuit_breakers", mock_circuit_breakers):
        response = client.get("/health/circuit-breakers")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "circuit_breakers" in data
    assert data["circuit_breakers"]["openai"]["state"] == "open"
    assert data["circuit_breakers"]["anthropic"]["state"] == "closed"


def test_circuit_breakers_half_open_returns_degraded(client):
    """Test GET /health/circuit-breakers when circuit is half-open (degraded)."""
    # Mock circuit breakers with HALF_OPEN state
    mock_circuit_breakers = {
        "openai": MagicMock(get_state=MagicMock(return_value={"state": "half_open", "failure_count": 3})),
        "anthropic": MagicMock(get_state=MagicMock(return_value={"state": "closed", "failure_count": 0}))
    }

    with patch("app.core.services.llm.gateway.llm_gateway.circuit_breakers", mock_circuit_breakers):
        response = client.get("/health/circuit-breakers")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "circuit_breakers" in data
    assert data["circuit_breakers"]["openai"]["state"] == "half_open"
