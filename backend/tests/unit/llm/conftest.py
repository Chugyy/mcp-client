"""Pytest configuration for LLM unit tests - overrides parent fixtures."""

import pytest


# Override parent autouse fixtures that we don't need for LLM tests
@pytest.fixture(autouse=True)
def mock_get_pool():
    """Override parent autouse async fixture - LLM tests don't use DB pool."""
    # Return None to satisfy fixture but don't do anything
    return None


@pytest.fixture(autouse=True)
def mock_settings():
    """Override parent autouse fixture - LLM tests mock settings individually."""
    # Return None to satisfy fixture but don't do anything
    return None
