# Database Migration Test Setup Guide

## Quick Start

### 1. Create Test Database

```bash
# Option A: Using your existing PostgreSQL user
psql -U <your_username> -d postgres -c "CREATE DATABASE test_backend;"

# Option B: Using Docker
docker run --name postgres-test \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=test_backend \
  -p 5432:5432 \
  -d postgres:14
```

### 2. Set Environment Variables

Create a `.env.test` file in `dev/backend/` with:

```bash
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=test_backend
TEST_DB_USER=<your_postgres_user>
TEST_DB_PASSWORD=<your_postgres_password>
```

Or export them:

```bash
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=test_backend
export TEST_DB_USER=<your_postgres_user>
export TEST_DB_PASSWORD=<your_postgres_password>
```

### 3. Run Tests

```bash
# From dev/backend directory
pytest tests/integration/database/test_migrations.py -v

# Run specific test
pytest tests/integration/database/test_migrations.py::test_all_migrations_execute_successfully -v

# Run with detailed output
pytest tests/integration/database/test_migrations.py -v -s
```

## Docker Compose Setup (Recommended)

Create `docker-compose.test.yml` in `dev/backend/`:

```yaml
version: '3.8'

services:
  test-db:
    image: postgres:14
    environment:
      POSTGRES_DB: test_backend
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"  # Use different port to avoid conflicts
    volumes:
      - test-db-data:/var/lib/postgresql/data

volumes:
  test-db-data:
```

Start test database:

```bash
docker-compose -f docker-compose.test.yml up -d
```

Run tests:

```bash
export TEST_DB_PORT=5433
export TEST_DB_USER=test_user
export TEST_DB_PASSWORD=test_password
pytest tests/integration/database/test_migrations.py -v
```

Stop test database:

```bash
docker-compose -f docker-compose.test.yml down -v
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Migration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: test_backend
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd dev/backend
          pip install -r requirements.txt

      - name: Run migration tests
        env:
          TEST_DB_HOST: localhost
          TEST_DB_PORT: 5432
          TEST_DB_NAME: test_backend
          TEST_DB_USER: test_user
          TEST_DB_PASSWORD: test_password
        run: |
          cd dev/backend
          pytest tests/integration/database/test_migrations.py -v
```

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
psql --version
pg_isready -h localhost -p 5432

# Check Docker container
docker ps | grep postgres
docker logs postgres-test
```

### Authentication Failed

```bash
# Verify user exists
psql -U postgres -c "SELECT usename FROM pg_user;"

# Grant privileges
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE test_backend TO <your_user>;"
```

### Tests Fail with "schema already exists"

The tests should clean up automatically, but if needed:

```bash
# Connect to test database
psql -U <your_user> -d test_backend

# Drop all schemas
DROP SCHEMA IF EXISTS core, agents, chat, mcp, resources, audit, automation CASCADE;
DROP TABLE IF EXISTS _migrations CASCADE;
```

## Test Performance

Expected performance on a standard development machine:
- Full test suite: < 2 minutes
- Individual migration test: < 5 seconds
- Idempotence test: < 10 seconds

For parallel execution (requires pytest-xdist):

```bash
pip install pytest-xdist
pytest tests/integration/database/test_migrations.py -v -n auto
```
