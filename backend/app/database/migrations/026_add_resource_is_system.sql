-- ============================================================================
-- Migration 026: Add is_system flag to resources table
-- ============================================================================
-- Description: Add system flag to resources for protected system resources
-- ============================================================================

BEGIN;

-- Add is_system column to resources table
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'resources' AND column_name = 'is_system'
    ) THEN
        ALTER TABLE resources ADD COLUMN is_system BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Create partial index for performance (only index system resources)
CREATE INDEX IF NOT EXISTS idx_resources_system ON resources(is_system) WHERE is_system = true;

-- Add comment
COMMENT ON COLUMN resources.is_system IS 'System-level resources cannot be deleted or modified by regular users. Only super-admins can manage system resources.';

-- Verification
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'resources' AND column_name = 'is_system'
    ) THEN
        RAISE EXCEPTION 'Column resources.is_system does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'resources' AND indexname = 'idx_resources_system'
    ) THEN
        RAISE EXCEPTION 'Index idx_resources_system does not exist';
    END IF;

    RAISE NOTICE 'Migration 026 completed successfully: is_system column added to resources table';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Migration is idempotent and can be run multiple times safely
-- 2. Conditional index (WHERE is_system = true) saves space and improves performance
-- 3. System resources should be set via admin interface or direct SQL
-- 4. Example: UPDATE resources SET is_system = true WHERE id = 'res_abc123';
-- ============================================================================
