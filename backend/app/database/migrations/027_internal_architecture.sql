-- ============================================================================
-- Migration 027: Internal Architecture
-- ============================================================================
-- Description: Add user_id and visibility flags for internal architecture
--   - Add user_id to servers and resources for multi-tenancy
--   - Rename __system__ to __internal__ in all data
--   - Add is_public flags for visibility control
--   - Add is_default and is_removable flags for tools
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Add user_id columns
-- ============================================================================

-- Add user_id to mcp.servers
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE mcp.servers ADD COLUMN user_id TEXT REFERENCES core.users(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_servers_user_id ON mcp.servers(user_id);

-- Add user_id to resources.resources
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'resources' AND table_name = 'resources' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE resources.resources ADD COLUMN user_id TEXT REFERENCES core.users(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_resources_user_id ON resources.resources(user_id);

-- ============================================================================
-- STEP 2: Rename __system__ to __internal__ in all tables
-- ============================================================================

-- Create __internal__ user if __system__ exists
DO $$
DECLARE
    v_system_user RECORD;
BEGIN
    -- Check if __system__ user exists
    SELECT * INTO v_system_user FROM core.users WHERE id = '__system__';

    IF FOUND THEN
        -- Create __internal__ user with same data as __system__ (but unique email)
        INSERT INTO core.users (id, email, password, name, preferences, is_system, created_at, updated_at)
        SELECT '__internal__', 'internal@system', password, 'Internal System', preferences, is_system, created_at, updated_at
        FROM core.users WHERE id = '__system__'
        ON CONFLICT (id) DO NOTHING;

        -- Update all referencing tables
        UPDATE agents.agents SET user_id = '__internal__' WHERE user_id = '__system__';
        UPDATE mcp.servers SET user_id = '__internal__' WHERE user_id = '__system__';
        UPDATE resources.resources SET user_id = '__internal__' WHERE user_id = '__system__';

        -- Update chat.chats if column exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'chat' AND table_name = 'chats' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'UPDATE chat.chats SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        -- Update automation tables if they exist
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'automation' AND table_name = 'automations'
        ) THEN
            EXECUTE 'UPDATE automation.automations SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'automation' AND table_name = 'executions'
        ) THEN
            EXECUTE 'UPDATE automation.executions SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        -- Update audit tables
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'audit' AND table_name = 'logs'
        ) THEN
            EXECUTE 'UPDATE audit.logs SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'audit' AND table_name = 'validations'
        ) THEN
            EXECUTE 'UPDATE audit.validations SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        -- Update other tables that might have user_id
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'core' AND table_name = 'api_keys' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'UPDATE core.api_keys SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'core' AND table_name = 'user_providers' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'UPDATE core.user_providers SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'resources' AND table_name = 'uploads' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'UPDATE resources.uploads SET user_id = ''__internal__'' WHERE user_id = ''__system__''';
        END IF;

        -- Delete __system__ user (all references have been migrated)
        DELETE FROM core.users WHERE id = '__system__';

        RAISE NOTICE 'Successfully renamed __system__ to __internal__';
    ELSE
        RAISE NOTICE '__system__ user does not exist, skipping rename';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Add is_public columns
-- ============================================================================

-- Add is_public to agents.agents
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'agents' AND table_name = 'agents' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE agents.agents ADD COLUMN is_public BOOLEAN DEFAULT false;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_agents_public ON agents.agents(is_public) WHERE is_public = true;

-- Add is_public to mcp.servers
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE mcp.servers ADD COLUMN is_public BOOLEAN DEFAULT false;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_servers_public ON mcp.servers(is_public) WHERE is_public = true;

-- Add is_public to resources.resources
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'resources' AND table_name = 'resources' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE resources.resources ADD COLUMN is_public BOOLEAN DEFAULT false;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_resources_public ON resources.resources(is_public) WHERE is_public = true;

-- ============================================================================
-- STEP 4: Add tool management columns
-- ============================================================================

-- Add is_default to mcp.tools
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'tools' AND column_name = 'is_default'
    ) THEN
        ALTER TABLE mcp.tools ADD COLUMN is_default BOOLEAN DEFAULT false;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tools_default ON mcp.tools(is_default) WHERE is_default = true;

-- Add is_removable to mcp.tools
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'tools' AND column_name = 'is_removable'
    ) THEN
        ALTER TABLE mcp.tools ADD COLUMN is_removable BOOLEAN DEFAULT true;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Add comments
-- ============================================================================

COMMENT ON COLUMN mcp.servers.user_id IS 'Owner of the MCP server. __internal__ for system servers.';
COMMENT ON COLUMN mcp.servers.is_public IS 'Public servers are visible to all users.';
COMMENT ON COLUMN resources.resources.user_id IS 'Owner of the resource. __internal__ for system resources.';
COMMENT ON COLUMN resources.resources.is_public IS 'Public resources are visible to all users.';
COMMENT ON COLUMN agents.agents.is_public IS 'Public agents are visible to all users.';
COMMENT ON COLUMN mcp.tools.is_default IS 'Default tools are automatically attached to all agents.';
COMMENT ON COLUMN mcp.tools.is_removable IS 'Non-removable tools cannot be detached from agents.';

-- ============================================================================
-- STEP 6: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify mcp.servers columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'Column mcp.servers.user_id does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'is_public'
    ) THEN
        RAISE EXCEPTION 'Column mcp.servers.is_public does not exist';
    END IF;

    -- Verify resources.resources columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'resources' AND table_name = 'resources' AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'Column resources.resources.user_id does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'resources' AND table_name = 'resources' AND column_name = 'is_public'
    ) THEN
        RAISE EXCEPTION 'Column resources.resources.is_public does not exist';
    END IF;

    -- Verify agents.agents columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'agents' AND table_name = 'agents' AND column_name = 'is_public'
    ) THEN
        RAISE EXCEPTION 'Column agents.agents.is_public does not exist';
    END IF;

    -- Verify mcp.tools columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'tools' AND column_name = 'is_default'
    ) THEN
        RAISE EXCEPTION 'Column mcp.tools.is_default does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'tools' AND column_name = 'is_removable'
    ) THEN
        RAISE EXCEPTION 'Column mcp.tools.is_removable does not exist';
    END IF;

    -- Verify indexes
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'mcp' AND tablename = 'servers' AND indexname = 'idx_servers_user_id'
    ) THEN
        RAISE EXCEPTION 'Index idx_servers_user_id does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'resources' AND tablename = 'resources' AND indexname = 'idx_resources_user_id'
    ) THEN
        RAISE EXCEPTION 'Index idx_resources_user_id does not exist';
    END IF;

    RAISE NOTICE 'Migration 027 completed successfully: Internal architecture columns added';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Migration is idempotent and can be run multiple times safely
-- 2. __system__ is renamed to __internal__ for consistency
-- 3. is_public allows internal entities to be visible to all users
-- 4. is_default tools are automatically attached to all agents
-- 5. is_removable=false prevents tools from being detached
-- ============================================================================
