-- Migration 013: Create PostgreSQL Schemas and Organize Tables
-- Description: Create modular schemas (core, agents, chat, mcp, resources, audit)
--              and move existing tables to appropriate schemas

-- ============================================================================
-- STEP 1: Create Schemas
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS mcp;
CREATE SCHEMA IF NOT EXISTS resources;
CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================================
-- STEP 2: Move Tables to Appropriate Schemas
-- ============================================================================

-- Core schema: Users, Authentication, Services
ALTER TABLE IF EXISTS users SET SCHEMA core;
ALTER TABLE IF EXISTS reset_tokens SET SCHEMA core;
ALTER TABLE IF EXISTS api_keys SET SCHEMA core;
ALTER TABLE IF EXISTS services SET SCHEMA core;
ALTER TABLE IF EXISTS models SET SCHEMA core;
ALTER TABLE IF EXISTS user_providers SET SCHEMA core;

-- Agents schema: Agents, Teams, Configurations
ALTER TABLE IF EXISTS agents SET SCHEMA agents;
ALTER TABLE IF EXISTS teams SET SCHEMA agents;
ALTER TABLE IF EXISTS memberships SET SCHEMA agents;
ALTER TABLE IF EXISTS configurations SET SCHEMA agents;

-- Chat schema: Chats, Messages
ALTER TABLE IF EXISTS chats SET SCHEMA chat;
ALTER TABLE IF EXISTS messages SET SCHEMA chat;

-- MCP schema: Servers, Tools, OAuth
ALTER TABLE IF EXISTS servers SET SCHEMA mcp;
ALTER TABLE IF EXISTS tools SET SCHEMA mcp;
ALTER TABLE IF EXISTS oauth_tokens SET SCHEMA mcp;

-- Resources schema: Resources, Uploads, Embeddings
ALTER TABLE IF EXISTS resources SET SCHEMA resources;
ALTER TABLE IF EXISTS uploads SET SCHEMA resources;
ALTER TABLE IF EXISTS embeddings SET SCHEMA resources;

-- Audit schema: Logs, Validations
ALTER TABLE IF EXISTS logs SET SCHEMA audit;
ALTER TABLE IF EXISTS validations SET SCHEMA audit;

-- ============================================================================
-- STEP 3: Update Foreign Key References (if needed)
-- ============================================================================

-- PostgreSQL automatically updates FK references when tables are moved to new schemas
-- But we verify critical cross-schema FKs exist

-- Verify agents.agents references core.users
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
        AND table_schema = 'agents'
        AND table_name = 'agents'
        AND constraint_name LIKE '%user_id%'
    ) THEN
        RAISE EXCEPTION 'Missing FK: agents.agents.user_id -> core.users.id';
    END IF;
END $$;

-- Verify chat.chats references core.users and agents.agents
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
        AND table_schema = 'chat'
        AND table_name = 'chats'
        AND constraint_name LIKE '%user_id%'
    ) THEN
        RAISE EXCEPTION 'Missing FK: chat.chats.user_id -> core.users.id';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Create Indexes for Cross-Schema Queries (if not already exist)
-- ============================================================================

-- Index on agents.agents.user_id (for filtering by user)
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents.agents(user_id);

-- Index on chat.chats.user_id and agent_id
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chat.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_agent_id ON chat.chats(agent_id);

-- Index on audit.logs.user_id and agent_id
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON audit.logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_agent_id ON audit.logs(agent_id);

-- Index on audit.validations.user_id
CREATE INDEX IF NOT EXISTS idx_validations_user_id ON audit.validations(user_id);

-- ============================================================================
-- STEP 5: Grant Permissions (Production-Ready)
-- ============================================================================

-- Revoke CREATE privilege on public schema (security best practice)
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Grant USAGE on all schemas to database owner
-- Note: Replace 'your_db_user' with actual database user
-- GRANT USAGE ON SCHEMA core, agents, chat, mcp, resources, audit TO your_db_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core, agents, chat, mcp, resources, audit TO your_db_user;

-- For production, create specific roles per module (example commented)
-- CREATE ROLE app_backend;
-- GRANT USAGE ON SCHEMA core, agents, chat, mcp, resources, audit TO app_backend;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core, agents, chat, mcp, resources, audit TO app_backend;

-- ============================================================================
-- STEP 6: Verification
-- ============================================================================

-- Verify all schemas exist
DO $$
DECLARE
    required_schemas TEXT[] := ARRAY['core', 'agents', 'chat', 'mcp', 'resources', 'audit'];
    v_schema_name TEXT;
BEGIN
    FOREACH v_schema_name IN ARRAY required_schemas
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.schemata WHERE schema_name = v_schema_name
        ) THEN
            RAISE EXCEPTION 'Schema % does not exist', v_schema_name;
        END IF;
    END LOOP;
    RAISE NOTICE 'All required schemas exist';
END $$;

-- Verify tables moved to correct schemas
DO $$
BEGIN
    -- Check core schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'core' AND table_name = 'users') THEN
        RAISE EXCEPTION 'Table core.users does not exist';
    END IF;

    -- Check agents schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'agents' AND table_name = 'agents') THEN
        RAISE EXCEPTION 'Table agents.agents does not exist';
    END IF;

    -- Check chat schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chat' AND table_name = 'chats') THEN
        RAISE EXCEPTION 'Table chat.chats does not exist';
    END IF;

    -- Check mcp schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'mcp' AND table_name = 'servers') THEN
        RAISE EXCEPTION 'Table mcp.servers does not exist';
    END IF;

    -- Check resources schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'resources' AND table_name = 'resources') THEN
        RAISE EXCEPTION 'Table resources.resources does not exist';
    END IF;

    -- Check audit schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'audit' AND table_name = 'logs') THEN
        RAISE EXCEPTION 'Table audit.logs does not exist';
    END IF;

    RAISE NOTICE 'All tables successfully moved to appropriate schemas';
END $$;

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. search_path will be configured at connection level in db.py
-- 2. This migration is idempotent (can be run multiple times safely)
-- 3. Foreign keys are automatically updated when tables are moved
-- 4. Existing indexes are preserved
-- 5. Data is NOT lost during table move (schema change only)
-- 6. Application code will need to be updated to use new schemas (via search_path or explicit qualification)
