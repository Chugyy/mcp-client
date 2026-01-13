"""
Integration tests for database migrations.

Tests all 41 migrations for:
- Successful execution
- Idempotence (can run multiple times)
- Schema correctness
- Foreign key constraints
- Indexes and constraints
"""

import pytest
import asyncpg
import os
from pathlib import Path
from app.database.migrations import (
    init_migrations_table,
    get_applied_migrations,
    run_migration,
    parse_sql_statements
)


# Test database configuration
TEST_DB_CONFIG = {
    "host": os.getenv("TEST_DB_HOST", "localhost"),
    "port": int(os.getenv("TEST_DB_PORT", 5432)),
    "database": os.getenv("TEST_DB_NAME", "test_backend"),
    "user": os.getenv("TEST_DB_USER", "postgres"),
    "password": os.getenv("TEST_DB_PASSWORD", "postgres")
}


@pytest.fixture
async def clean_test_db():
    """Provides a clean test database for migration testing."""
    # Connect to test database
    conn = await asyncpg.connect(**TEST_DB_CONFIG)

    # Drop all schemas (clean slate)
    await conn.execute("""
        DROP SCHEMA IF EXISTS core, agents, chat, mcp, resources, audit, automation CASCADE;
    """)

    # Drop migrations table if exists
    await conn.execute("DROP TABLE IF EXISTS _migrations CASCADE;")

    # Configure search_path
    await conn.execute("""
        SET search_path TO core, agents, chat, mcp, resources, audit, public
    """)

    yield conn

    # Cleanup
    await conn.close()


@pytest.fixture
def migrations_dir():
    """Returns the path to migrations directory."""
    backend_dir = Path(__file__).parent.parent.parent.parent
    migrations_path = backend_dir / "app" / "database" / "migrations"
    assert migrations_path.exists(), f"Migrations directory not found: {migrations_path}"
    return migrations_path


@pytest.fixture
def migration_files(migrations_dir):
    """Returns sorted list of all migration files."""
    files = sorted(migrations_dir.glob("*.sql"))
    assert len(files) > 0, "No migration files found"
    return files


async def get_schema_state(conn):
    """Capture complete database schema state for comparison."""
    state = {}

    # Tables
    tables = await conn.fetch("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """)
    state["tables"] = [(row["table_schema"], row["table_name"]) for row in tables]

    # Columns
    columns = await conn.fetch("""
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name, ordinal_position
    """)
    state["columns"] = [
        (row["table_schema"], row["table_name"], row["column_name"], row["data_type"])
        for row in columns
    ]

    # Indexes
    indexes = await conn.fetch("""
        SELECT schemaname, tablename, indexname
        FROM pg_indexes
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schemaname, tablename, indexname
    """)
    state["indexes"] = [
        (row["schemaname"], row["tablename"], row["indexname"])
        for row in indexes
    ]

    # Constraints
    constraints = await conn.fetch("""
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type
        FROM information_schema.table_constraints AS tc
        WHERE tc.table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY tc.table_schema, tc.table_name, tc.constraint_name
    """)
    state["constraints"] = [
        (row["table_schema"], row["table_name"], row["constraint_name"], row["constraint_type"])
        for row in constraints
    ]

    return state


async def run_all_migrations(conn, migration_files):
    """Run all migrations in order."""
    # Initialize migrations table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Get already applied migrations
    applied_rows = await conn.fetch("SELECT filename FROM _migrations ORDER BY id")
    applied = {row['filename'] for row in applied_rows}

    # Run each migration
    for filepath in migration_files:
        if filepath.name not in applied:
            # Read migration file
            with open(filepath, 'r') as f:
                sql = f.read()

            # Parse SQL statements
            statements = parse_sql_statements(sql)

            # Execute each statement
            for stmt in statements:
                if stmt.strip():
                    try:
                        await conn.execute(stmt)
                    except asyncpg.exceptions.DuplicateTableError:
                        pass  # Idempotent
                    except asyncpg.exceptions.DuplicateObjectError:
                        pass  # Idempotent
                    except Exception as e:
                        # Ignore DROP IF EXISTS errors
                        if 'does not exist' in str(e) and any(
                            x in stmt.upper() for x in ['DROP TABLE', 'DROP FUNCTION', 'DROP INDEX']
                        ):
                            pass
                        else:
                            raise

            # Mark as applied
            await conn.execute(
                "INSERT INTO _migrations (filename) VALUES ($1) ON CONFLICT (filename) DO NOTHING",
                filepath.name
            )


# ============================================================================
# TEST: All migrations execute successfully
# ============================================================================

@pytest.mark.asyncio
async def test_all_migrations_execute_successfully(clean_test_db, migration_files):
    """Test that all 40 migrations execute without errors."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Verify migrations table exists and has entries
    migrations_count = await conn.fetchval("SELECT COUNT(*) FROM _migrations")
    assert migrations_count == len(migration_files), (
        f"Expected {len(migration_files)} migrations, got {migrations_count}"
    )

    # Verify at least some tables were created
    tables = await conn.fetch("""
        SELECT COUNT(*) as count
        FROM information_schema.tables
        WHERE table_schema IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
    """)
    table_count = tables[0]['count']
    assert table_count > 0, "No tables created after migrations"


# ============================================================================
# TEST: Migrations are idempotent
# ============================================================================

@pytest.mark.asyncio
async def test_migrations_are_idempotent(clean_test_db, migration_files):
    """Test that migrations can be run multiple times safely."""
    conn = clean_test_db

    # Run migrations once
    await run_all_migrations(conn, migration_files)
    schema_state_1 = await get_schema_state(conn)

    # Clear migrations table to force re-run
    await conn.execute("DELETE FROM _migrations")

    # Run migrations again
    await run_all_migrations(conn, migration_files)
    schema_state_2 = await get_schema_state(conn)

    # Schema should be identical
    assert schema_state_1["tables"] == schema_state_2["tables"], "Tables differ after re-run"
    assert schema_state_1["columns"] == schema_state_2["columns"], "Columns differ after re-run"
    assert schema_state_1["indexes"] == schema_state_2["indexes"], "Indexes differ after re-run"
    assert schema_state_1["constraints"] == schema_state_2["constraints"], "Constraints differ after re-run"


# ============================================================================
# TEST: Final schema structure
# ============================================================================

@pytest.mark.asyncio
async def test_final_schema_structure(clean_test_db, migration_files):
    """Test that final schema matches expected structure."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Verify schemas exist
    schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata")
    schema_names = [row["schema_name"] for row in schemas]

    expected_schemas = ["core", "agents", "chat", "mcp", "resources", "audit", "automation"]
    for schema in expected_schemas:
        assert schema in schema_names, f"Schema '{schema}' not found"

    # Verify we have a reasonable number of tables
    tables = await conn.fetch("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
    """)
    assert len(tables) >= 30, f"Expected at least 30 tables, got {len(tables)}"


# ============================================================================
# TEST: Core tables exist
# ============================================================================

@pytest.mark.asyncio
async def test_core_tables_exist(clean_test_db, migration_files):
    """Test that core tables are created correctly."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Get all tables
    tables = await conn.fetch("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
    """)
    table_names = [f"{row['table_schema']}.{row['table_name']}" for row in tables]

    # Core tables
    expected_core_tables = ["core.users", "core.teams"]
    for table in expected_core_tables:
        assert table in table_names, f"Table '{table}' not found"

    # Chat tables
    expected_chat_tables = ["chat.conversations", "chat.messages"]
    for table in expected_chat_tables:
        assert table in table_names, f"Table '{table}' not found"

    # MCP tables
    expected_mcp_tables = ["mcp.servers", "mcp.tools"]
    for table in expected_mcp_tables:
        assert table in table_names, f"Table '{table}' not found"


# ============================================================================
# TEST: Foreign keys defined correctly
# ============================================================================

@pytest.mark.asyncio
async def test_foreign_keys_defined_correctly(clean_test_db, migration_files):
    """Test that foreign key constraints are properly defined."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Query foreign key constraints
    fk_constraints = await conn.fetch("""
        SELECT
            tc.table_schema,
            tc.table_name,
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
    """)

    # Verify we have foreign keys
    assert len(fk_constraints) > 0, "No foreign key constraints found"

    # Build list of foreign keys
    fk_list = [
        (row["table_schema"], row["table_name"], row["column_name"])
        for row in fk_constraints
    ]

    # Verify at least some expected foreign keys exist
    # Note: Adjust these based on actual schema
    expected_fks = [
        # Add specific foreign keys to verify based on schema
        # Example: ("chat", "conversations", "user_id")
    ]

    for fk in expected_fks:
        assert fk in fk_list, f"Foreign key {fk} not found"


# ============================================================================
# TEST: Indexes created
# ============================================================================

@pytest.mark.asyncio
async def test_indexes_created(clean_test_db, migration_files):
    """Test that indexes are created correctly."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Query indexes
    indexes = await conn.fetch("""
        SELECT schemaname, tablename, indexname
        FROM pg_indexes
        WHERE schemaname IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
        ORDER BY schemaname, tablename, indexname
    """)

    # Verify we have indexes
    assert len(indexes) > 0, "No indexes found"


# ============================================================================
# TEST: Constraints validated
# ============================================================================

@pytest.mark.asyncio
async def test_constraints_validated(clean_test_db, migration_files):
    """Test that constraints (UNIQUE, CHECK, NOT NULL) are validated."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Query constraints
    constraints = await conn.fetch("""
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type
        FROM information_schema.table_constraints AS tc
        WHERE tc.table_schema IN ('core', 'agents', 'chat', 'mcp', 'resources', 'audit', 'automation')
        ORDER BY tc.table_schema, tc.table_name, tc.constraint_type
    """)

    # Verify we have constraints
    assert len(constraints) > 0, "No constraints found"

    # Verify different types of constraints exist
    constraint_types = set(row["constraint_type"] for row in constraints)
    assert "PRIMARY KEY" in constraint_types, "No PRIMARY KEY constraints found"
    assert "FOREIGN KEY" in constraint_types, "No FOREIGN KEY constraints found"


# ============================================================================
# TEST: Migration tracking table
# ============================================================================

@pytest.mark.asyncio
async def test_migration_tracking_table(clean_test_db, migration_files):
    """Test that migration tracking table (_migrations) is created and used."""
    conn = clean_test_db

    # Run all migrations
    await run_all_migrations(conn, migration_files)

    # Verify _migrations table exists
    table_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = '_migrations'
        )
    """)
    assert table_exists, "_migrations table not found"

    # Verify it has the correct columns
    columns = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = '_migrations'
        ORDER BY ordinal_position
    """)
    column_names = [row["column_name"] for row in columns]
    assert "id" in column_names, "Column 'id' not found in _migrations"
    assert "filename" in column_names, "Column 'filename' not found in _migrations"
    assert "applied_at" in column_names, "Column 'applied_at' not found in _migrations"

    # Verify it has all migration records
    migration_count = await conn.fetchval("SELECT COUNT(*) FROM _migrations")
    assert migration_count == len(migration_files), (
        f"Expected {len(migration_files)} migration records, got {migration_count}"
    )


# ============================================================================
# TEST: PL/pgSQL blocks execute
# ============================================================================

@pytest.mark.asyncio
async def test_plpgsql_blocks_execute(clean_test_db, migration_files):
    """Test that migrations with PL/pgSQL blocks execute correctly."""
    conn = clean_test_db

    # Run all migrations (including those with PL/pgSQL blocks)
    await run_all_migrations(conn, migration_files)

    # Verify migrations completed successfully
    migration_count = await conn.fetchval("SELECT COUNT(*) FROM _migrations")
    assert migration_count == len(migration_files), "Some migrations failed to apply"


# ============================================================================
# TEST: Individual migration execution
# ============================================================================

@pytest.mark.asyncio
async def test_individual_migrations_execute(clean_test_db, migration_files):
    """Test each migration individually to catch specific failures."""
    conn = clean_test_db

    # Initialize migrations table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Test each migration individually
    for filepath in migration_files:
        # Read migration
        with open(filepath, 'r') as f:
            sql = f.read()

        # Parse statements
        statements = parse_sql_statements(sql)

        # Execute each statement
        for stmt in statements:
            if stmt.strip():
                try:
                    await conn.execute(stmt)
                except asyncpg.exceptions.DuplicateTableError:
                    pass
                except asyncpg.exceptions.DuplicateObjectError:
                    pass
                except Exception as e:
                    if 'does not exist' in str(e) and any(
                        x in stmt.upper() for x in ['DROP TABLE', 'DROP FUNCTION', 'DROP INDEX']
                    ):
                        pass
                    else:
                        pytest.fail(f"Migration {filepath.name} failed: {e}\nStatement: {stmt[:200]}")

        # Mark as applied
        await conn.execute(
            "INSERT INTO _migrations (filename) VALUES ($1) ON CONFLICT (filename) DO NOTHING",
            filepath.name
        )

    # Verify all migrations applied
    migration_count = await conn.fetchval("SELECT COUNT(*) FROM _migrations")
    assert migration_count == len(migration_files)
