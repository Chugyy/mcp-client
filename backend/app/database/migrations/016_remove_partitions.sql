-- ============================================================================
-- Migration 016: Remove Partitions from execution_step_logs
-- ============================================================================
-- Description: Replace partitioned table with standard table + indexes
--   - Drop partitioned execution_step_logs table
--   - Create standard table with same schema
--   - Add performance indexes
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Drop partitioned table and all partitions
-- ============================================================================

DROP TABLE IF EXISTS automation.execution_step_logs CASCADE;

-- ============================================================================
-- STEP 2: Create standard table (no partitions)
-- ============================================================================

CREATE TABLE automation.execution_step_logs (
  id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('log'),
  execution_id TEXT NOT NULL,
  step_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'skipped')),
  result JSONB,
  error TEXT,
  duration_ms INTEGER,
  executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- STEP 3: Create performance indexes
-- ============================================================================

CREATE INDEX idx_execution_step_logs_execution_id ON automation.execution_step_logs(execution_id);
CREATE INDEX idx_execution_step_logs_step_id ON automation.execution_step_logs(step_id);
CREATE INDEX idx_execution_step_logs_status ON automation.execution_step_logs(status);
CREATE INDEX idx_execution_step_logs_executed_at ON automation.execution_step_logs(executed_at DESC);

-- ============================================================================
-- STEP 4: Add table and column comments
-- ============================================================================

COMMENT ON TABLE automation.execution_step_logs IS
'Detailed logs for each workflow step execution.
Uses standard B-tree indexes for performance instead of partitioning.';

COMMENT ON COLUMN automation.execution_step_logs.status IS
'Step execution status:
- running: Currently executing
- success: Completed successfully
- failed: Failed with error
- skipped: Skipped due to run_condition';

COMMENT ON COLUMN automation.execution_step_logs.duration_ms IS
'Execution duration in milliseconds.';

-- ============================================================================
-- STEP 5: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'execution_step_logs') THEN
        RAISE EXCEPTION 'Table automation.execution_step_logs does not exist';
    END IF;

    -- Verify it's NOT partitioned
    IF EXISTS (SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'automation.execution_step_logs'::regclass) THEN
        RAISE EXCEPTION 'Table automation.execution_step_logs should NOT be partitioned';
    END IF;

    -- Verify PRIMARY KEY exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'automation'
          AND table_name = 'execution_step_logs'
          AND constraint_type = 'PRIMARY KEY'
    ) THEN
        RAISE EXCEPTION 'PRIMARY KEY missing on automation.execution_step_logs';
    END IF;

    RAISE NOTICE 'Migration 016 completed successfully - execution_step_logs is now a standard table with indexes';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. This migration removes the partition-based architecture
-- 2. Performance is maintained via standard B-tree indexes
-- 3. No more monthly partition creation needed
-- 4. Simpler schema, easier maintenance
-- ============================================================================
