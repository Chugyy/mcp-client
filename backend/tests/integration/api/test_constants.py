"""Test constants for API integration tests.

Centralizes test data to avoid magic strings and improve maintainability.
"""

import os

# Database Configuration
TEST_DB_HOST = os.getenv("TEST_DB_HOST", "localhost")
TEST_DB_PORT = int(os.getenv("TEST_DB_PORT", "5432"))
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "test_backend")
TEST_DB_USER = os.getenv("TEST_DB_USER", "hugohoarau")
TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", "")

# Test User Data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_NAME = "Test User"

# Other User Data (for permission tests)
OTHER_USER_EMAIL = "other@example.com"
OTHER_USER_PASSWORD = "otherpass123"
OTHER_USER_NAME = "Other User"

# Database Schema Search Path
DB_SEARCH_PATH = "core, agents, chat, mcp, resources, audit, automation, public"
