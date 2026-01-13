-- ============================================================================
-- Migration 029: Validation Improvements
-- ============================================================================
-- Description: Add execution tracking, expiration for validations, and chat tracking
-- ============================================================================

BEGIN;

-- Add execution_id to link validations with automation executions
ALTER TABLE validations
ADD COLUMN IF NOT EXISTS execution_id TEXT REFERENCES automation.executions(id) ON DELETE CASCADE;

-- Add expired_at for tracking expired validations
ALTER TABLE validations
ADD COLUMN IF NOT EXISTS expired_at TIMESTAMP;

-- Create index for execution_id
CREATE INDEX IF NOT EXISTS idx_validations_execution_id ON validations(execution_id);

-- Add awaiting_validation_id to chats table
ALTER TABLE chats
ADD COLUMN IF NOT EXISTS awaiting_validation_id TEXT REFERENCES validations(id) ON DELETE SET NULL;

COMMENT ON COLUMN validations.execution_id IS
'Links this validation to an automation execution.
Used to track which execution is waiting for this validation.';

COMMENT ON COLUMN validations.expired_at IS
'Timestamp when this validation was expired (timeout).
NULL if validation is not expired.';

COMMENT ON COLUMN chats.awaiting_validation_id IS
'ID of the validation this chat is currently waiting for.
NULL if chat is not waiting for any validation.';

COMMIT;
