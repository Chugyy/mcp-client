-- ============================================================================
-- Migration 040: Automation Validation Constraints
-- ============================================================================
-- Description: Add validation constraints and indexes for automations
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Add UNIQUE constraint on (name, user_id)
-- ============================================================================

-- Vérifier s'il y a des doublons avant d'ajouter la contrainte
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT name, user_id, COUNT(*)
        FROM automation.automations
        GROUP BY name, user_id
        HAVING COUNT(*) > 1
    ) AS duplicates;

    IF duplicate_count > 0 THEN
        RAISE WARNING 'Found % duplicate automation names. These will need to be resolved manually.', duplicate_count;
        RAISE NOTICE 'To resolve duplicates, you can run:';
        RAISE NOTICE 'SELECT name, user_id, COUNT(*) FROM automation.automations GROUP BY name, user_id HAVING COUNT(*) > 1;';
    END IF;
END $$;

-- Ajouter la contrainte UNIQUE (ignorera si doublons existent)
DO $$
BEGIN
    ALTER TABLE automation.automations
    ADD CONSTRAINT automations_name_user_unique
    UNIQUE(name, user_id);
EXCEPTION
    WHEN unique_violation THEN
        RAISE WARNING 'Cannot add UNIQUE constraint due to existing duplicates. Please resolve duplicates first.';
    WHEN duplicate_table THEN
        RAISE NOTICE 'Constraint automations_name_user_unique already exists';
END $$;

-- ============================================================================
-- STEP 2: Add performance indexes
-- ============================================================================

-- Index for name search
CREATE INDEX IF NOT EXISTS idx_automations_name
ON automation.automations(name);

-- Index for triggers (automation + enabled)
CREATE INDEX IF NOT EXISTS idx_triggers_automation_enabled
ON automation.triggers(automation_id, enabled)
WHERE enabled = true;

-- Index for workflow steps (automation + enabled)
CREATE INDEX IF NOT EXISTS idx_workflow_steps_automation_enabled
ON automation.workflow_steps(automation_id, enabled)
WHERE enabled = true;

-- Index for user_id (performance pour quota)
CREATE INDEX IF NOT EXISTS idx_automations_user_id
ON automation.automations(user_id);

-- ============================================================================
-- STEP 3: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify indexes exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'automation'
        AND indexname = 'idx_automations_name'
    ) THEN
        RAISE WARNING 'Index idx_automations_name does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'automation'
        AND indexname = 'idx_triggers_automation_enabled'
    ) THEN
        RAISE WARNING 'Index idx_triggers_automation_enabled does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'automation'
        AND indexname = 'idx_workflow_steps_automation_enabled'
    ) THEN
        RAISE WARNING 'Index idx_workflow_steps_automation_enabled does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'automation'
        AND indexname = 'idx_automations_user_id'
    ) THEN
        RAISE WARNING 'Index idx_automations_user_id does not exist';
    END IF;

    RAISE NOTICE 'Migration 040 completed successfully';
END $$;

COMMIT;
