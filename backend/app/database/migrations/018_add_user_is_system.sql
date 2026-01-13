-- ============================================================================
-- Migration 018: Add is_system flag to users table
-- ============================================================================
-- Description: Add super-admin flag to users table for system-level access
-- ============================================================================

BEGIN;

-- Add is_system column to users table
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'core' AND table_name = 'users' AND column_name = 'is_system'
    ) THEN
        ALTER TABLE core.users ADD COLUMN is_system BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Create index for is_system column (partial index for performance)
CREATE INDEX IF NOT EXISTS idx_users_system ON core.users(is_system) WHERE is_system = true;

-- Update admin user to be system user
UPDATE core.users SET is_system = true WHERE email = 'admin@admin.admin';

-- Add comment
COMMENT ON COLUMN core.users.is_system IS 'Super-admin flag (can access all resources)';

-- Verification
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'core' AND table_name = 'users' AND column_name = 'is_system'
    ) THEN
        RAISE EXCEPTION 'Column core.users.is_system does not exist';
    END IF;

    RAISE NOTICE 'Migration 018 completed successfully: is_system column added to users table';
END $$;

COMMIT;
