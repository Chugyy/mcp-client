-- ============================================================================
-- Migration 015: System Flags for Agents and MCP Servers
-- ============================================================================
-- Description: Add is_system flag to agents and servers for protected system resources
--   - Adds is_system BOOLEAN column to agents.agents
--   - Adds is_system BOOLEAN column to mcp.servers
--   - Creates conditional indexes for performance
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Add is_system flag to agents.agents
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'agents' AND table_name = 'agents' AND column_name = 'is_system'
  ) THEN
    ALTER TABLE agents.agents ADD COLUMN is_system BOOLEAN DEFAULT false;
  END IF;
END $$;

COMMENT ON COLUMN agents.agents.is_system IS
'System-level agents cannot be deleted or modified by regular users.
Only admins can manage system agents.';

-- ============================================================================
-- STEP 2: Add is_system flag to mcp.servers
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'is_system'
  ) THEN
    ALTER TABLE mcp.servers ADD COLUMN is_system BOOLEAN DEFAULT false;
  END IF;
END $$;

COMMENT ON COLUMN mcp.servers.is_system IS
'System-level MCP servers cannot be deleted or modified by regular users.
Only admins can manage system servers.';

-- ============================================================================
-- STEP 3: Create conditional indexes (only for is_system = true)
-- ============================================================================

-- Index for quick filtering of system agents
CREATE INDEX IF NOT EXISTS idx_agents_system ON agents.agents(is_system) WHERE is_system = true;

-- Index for quick filtering of system servers
CREATE INDEX IF NOT EXISTS idx_servers_system ON mcp.servers(is_system) WHERE is_system = true;

-- ============================================================================
-- STEP 4: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify agents.agents has is_system column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'agents' AND table_name = 'agents' AND column_name = 'is_system'
    ) THEN
        RAISE EXCEPTION 'Column agents.agents.is_system does not exist';
    END IF;

    -- Verify mcp.servers has is_system column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mcp' AND table_name = 'servers' AND column_name = 'is_system'
    ) THEN
        RAISE EXCEPTION 'Column mcp.servers.is_system does not exist';
    END IF;

    -- Verify indexes exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'agents' AND tablename = 'agents' AND indexname = 'idx_agents_system'
    ) THEN
        RAISE EXCEPTION 'Index idx_agents_system does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'mcp' AND tablename = 'servers' AND indexname = 'idx_servers_system'
    ) THEN
        RAISE EXCEPTION 'Index idx_servers_system does not exist';
    END IF;

    RAISE NOTICE 'System flags added successfully to agents.agents and mcp.servers';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Migration is idempotent and can be run multiple times safely
-- 2. Conditional indexes (WHERE is_system = true) save space and improve performance
-- 3. System resources should be set via admin interface or direct SQL
-- 4. Example: UPDATE agents.agents SET is_system = true WHERE id = 'agt_abc123';
-- ============================================================================
