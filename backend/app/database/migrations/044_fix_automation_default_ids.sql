-- ============================================================================
-- Migration 044: Fix automation tables DEFAULT values for id columns
-- ============================================================================
-- Description: Add missing DEFAULT core.generate_prefixed_id() to automation tables
--              that were created without proper schema qualification
-- ============================================================================

-- Fix automation.automations
ALTER TABLE automation.automations
  ALTER COLUMN id SET DEFAULT core.generate_prefixed_id('auto');

-- Fix automation.workflow_steps
ALTER TABLE automation.workflow_steps
  ALTER COLUMN id SET DEFAULT core.generate_prefixed_id('step');

-- Fix automation.triggers
ALTER TABLE automation.triggers
  ALTER COLUMN id SET DEFAULT core.generate_prefixed_id('trigger');

-- Fix automation.executions
ALTER TABLE automation.executions
  ALTER COLUMN id SET DEFAULT core.generate_prefixed_id('exec');

-- Fix automation.execution_step_logs (if id column exists with DEFAULT)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'automation'
        AND table_name = 'execution_step_logs'
        AND column_name = 'id'
    ) THEN
        ALTER TABLE automation.execution_step_logs
          ALTER COLUMN id SET DEFAULT core.generate_prefixed_id('log');
    END IF;
END $$;

-- Verification
DO $$
DECLARE
    v_default TEXT;
BEGIN
    -- Check automation.automations
    SELECT pg_get_expr(adbin, adrelid) INTO v_default
    FROM pg_attrdef
    JOIN pg_attribute ON pg_attribute.attrelid = pg_attrdef.adrelid AND pg_attribute.attnum = pg_attrdef.adnum
    JOIN pg_class ON pg_class.oid = pg_attrdef.adrelid
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    WHERE pg_namespace.nspname = 'automation'
    AND pg_class.relname = 'automations'
    AND pg_attribute.attname = 'id';

    IF v_default IS NULL OR v_default NOT LIKE '%generate_prefixed_id%' THEN
        RAISE EXCEPTION 'DEFAULT not set correctly on automation.automations.id';
    END IF;

    RAISE NOTICE '✅ Migration 044 completed: All DEFAULT values fixed';
END $$;
