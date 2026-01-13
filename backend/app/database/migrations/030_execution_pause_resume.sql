-- ============================================================================
-- Migration 030: Execution Pause/Resume
-- ============================================================================
-- Description: Add pause/resume functionality to automation executions
-- ============================================================================

BEGIN;

-- Add paused_at timestamp
ALTER TABLE automation.executions
ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP;

-- Add execution_state for storing workflow state during pause
ALTER TABLE automation.executions
ADD COLUMN IF NOT EXISTS execution_state JSONB;

-- Update status constraint to include 'paused'
ALTER TABLE automation.executions DROP CONSTRAINT IF EXISTS executions_status_check;
ALTER TABLE automation.executions ADD CONSTRAINT executions_status_check
CHECK (status IN ('running', 'success', 'failed', 'cancelled', 'paused'));

COMMENT ON COLUMN automation.executions.paused_at IS
'Timestamp when execution was paused.
NULL if execution is not paused.';

COMMENT ON COLUMN automation.executions.execution_state IS
'JSONB state for resuming execution after pause.
Contains: context, step_index, steps array.
Used to restore workflow state when resuming.';

COMMIT;
