-- ============================================================================
-- MIGRATION 042 : Add pending_authorization to server status constraint
-- ============================================================================
-- Context: OAuth servers need a 'pending_authorization' status during auth flow
-- This status is set when authorization_url is returned to the user
-- ============================================================================

-- Drop existing status check constraint on servers table
ALTER TABLE mcp.servers DROP CONSTRAINT IF EXISTS servers_status_check;

-- Recreate constraint with pending_authorization status
ALTER TABLE mcp.servers ADD CONSTRAINT servers_status_check
  CHECK (status IN ('pending', 'active', 'failed', 'unreachable', 'pending_authorization'));

-- Verify constraint was added
DO $$
BEGIN
    RAISE NOTICE 'Status constraint updated successfully - pending_authorization status added';
END $$;

-- ============================================================================
-- END OF MIGRATION 042
-- ============================================================================
