"""Pytest configuration for database integration tests.

These tests require a real PostgreSQL database connection.
The autouse mocks from the parent conftest are disabled here.
"""

import pytest


@pytest.fixture(autouse=True)
def disable_autouse_mocks():
    """Disable the autouse mocks from parent conftest for database integration tests."""
    # This fixture overrides the autouse fixtures from parent conftest.py
    # by being more specific (closer to the test files)
    pass
