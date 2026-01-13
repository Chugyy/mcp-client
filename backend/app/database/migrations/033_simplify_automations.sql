-- ============================================================================
-- Migration 033: Simplify Automations
-- ============================================================================
-- Description: Simplify automation model by removing status, permission_level, tags
--   - Remove status column (use only enabled boolean)
--   - Remove permission_level column (not needed, will use user-level permissions)
--   - Remove tags column (not used)
--   - Set enabled default to true
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Drop indexes on columns to be removed
-- ============================================================================

DROP INDEX IF EXISTS automation.idx_automations_status;
DROP INDEX IF EXISTS automation.idx_automations_tags;

-- ============================================================================
-- STEP 2: Remove columns from automations table
-- ============================================================================

ALTER TABLE automation.automations
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS permission_level,
  DROP COLUMN IF EXISTS tags;

-- ============================================================================
-- STEP 3: Update enabled column default to true
-- ============================================================================

ALTER TABLE automation.automations
  ALTER COLUMN enabled SET DEFAULT true;

-- ============================================================================
-- STEP 4: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify status column was removed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'automation'
        AND table_name = 'automations'
        AND column_name = 'status'
    ) THEN
        RAISE EXCEPTION 'Column status still exists in automation.automations';
    END IF;

    -- Verify permission_level column was removed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'automation'
        AND table_name = 'automations'
        AND column_name = 'permission_level'
    ) THEN
        RAISE EXCEPTION 'Column permission_level still exists in automation.automations';
    END IF;

    -- Verify tags column was removed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'automation'
        AND table_name = 'automations'
        AND column_name = 'tags'
    ) THEN
        RAISE EXCEPTION 'Column tags still exists in automation.automations';
    END IF;

    -- Verify enabled column default is true
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'automation'
        AND table_name = 'automations'
        AND column_name = 'enabled'
        AND column_default = 'true'
    ) THEN
        RAISE EXCEPTION 'Column enabled default is not true';
    END IF;

    RAISE NOTICE 'Automation table simplified successfully - removed status, permission_level, tags';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Automations now use only the 'enabled' boolean for state management
-- 2. Permission levels are managed at the user level, not per automation
-- 3. Tags have been removed as they were not actively used
-- 4. New automations will be enabled by default
-- ============================================================================
