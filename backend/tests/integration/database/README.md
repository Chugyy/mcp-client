# Database Migration Tests

## Purpose

These integration tests verify that all database migrations:
- Execute successfully without errors
- Are idempotent (can run multiple times)
- Create the correct schema structure
- Define foreign keys, indexes, and constraints correctly

## Test Database Setup

### Prerequisites

- PostgreSQL 13+ installed and running
- Python 3.11+ with pytest and asyncpg

### Create Test Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create test database
CREATE DATABASE test_backend;

# Create test user (if needed)
CREATE USER test_user WITH PASSWORD 'test_password';
GRANT ALL PRIVILEGES ON DATABASE test_backend TO test_user;

# Exit psql
\q
```

### Environment Variables

Set the following environment variables before running tests:

```bash
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=test_backend
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
```

Or create a `.env.test` file in the backend root directory.

## Running Tests

### Run all migration tests

```bash
pytest tests/integration/database/test_migrations.py -v
```

### Run specific test

```bash
pytest tests/integration/database/test_migrations.py::test_all_migrations_execute_successfully -v
```

### Run with output

```bash
pytest tests/integration/database/test_migrations.py -v -s
```

## Test Coverage

The test suite includes:

1. **test_all_migrations_execute_successfully**: Verifies all 40 migrations run without errors
2. **test_migrations_are_idempotent**: Verifies migrations can run multiple times safely
3. **test_final_schema_structure**: Verifies all 7 schemas are created
4. **test_core_tables_exist**: Verifies core tables exist in correct schemas
5. **test_foreign_keys_defined_correctly**: Verifies foreign key constraints
6. **test_indexes_created**: Verifies indexes are created
7. **test_constraints_validated**: Verifies PRIMARY KEY and other constraints
8. **test_migration_tracking_table**: Verifies _migrations table structure
9. **test_plpgsql_blocks_execute**: Verifies PL/pgSQL blocks execute correctly
10. **test_individual_migrations_execute**: Tests each migration individually

## Notes

- Tests use a clean database for each run (all schemas dropped before tests)
- Tests are safe to run repeatedly
- Test database is separate from development/production databases
- Migrations are tested in the order they would run in production
