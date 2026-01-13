-- ============================================================================
-- Migration 014: Automation System Schema
-- ============================================================================
-- Description: Create complete automation system with workflows, triggers, and execution tracking
--   - Schema automation with 5 tables
--   - Workflow management (automations, workflow_steps)
--   - Trigger system (cron, webhook, date, event, manual)
--   - Execution tracking with partitioned logs
--   - Support for permission levels and system automations
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Create Automation Schema
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS automation;

-- ============================================================================
-- STEP 2: Table automations (Main automation definitions)
-- ============================================================================

CREATE TABLE automation.automations (
  id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('auto'),
  user_id TEXT NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'archived')),
  permission_level TEXT NOT NULL DEFAULT 'validation_required' CHECK (permission_level IN ('full_auto', 'validation_required', 'no_tools')),
  is_system BOOLEAN DEFAULT false,
  tags TEXT[] DEFAULT '{}',
  enabled BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_automations_user_id ON automation.automations(user_id);
CREATE INDEX idx_automations_status ON automation.automations(status);
CREATE INDEX idx_automations_enabled ON automation.automations(enabled) WHERE enabled = true;
CREATE INDEX idx_automations_system ON automation.automations(is_system) WHERE is_system = true;
CREATE INDEX idx_automations_tags ON automation.automations USING GIN(tags);

COMMENT ON TABLE automation.automations IS
'Main automation definitions.
Each automation represents a workflow that can be triggered by various events.';

COMMENT ON COLUMN automation.automations.permission_level IS
'Permission level for tool execution within this automation:
- full_auto: All tools execute without validation
- validation_required: Requires validation before tool execution
- no_tools: Disables tool calling completely';

COMMENT ON COLUMN automation.automations.is_system IS
'System-level automations cannot be deleted by users and are managed by admins only.';

-- ============================================================================
-- STEP 3: Table workflow_steps (Sequential workflow steps)
-- ============================================================================

-- NOTE: La contrainte step_type a été corrigée par migration 031
CREATE TABLE automation.workflow_steps (
  id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('step'),
  automation_id TEXT NOT NULL REFERENCES automation.automations(id) ON DELETE CASCADE,
  step_order INTEGER NOT NULL,
  step_name TEXT NOT NULL,
  step_type TEXT NOT NULL CHECK (step_type IN ('action', 'control')),
  step_subtype TEXT,
  config JSONB DEFAULT '{}',
  run_condition TEXT,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(automation_id, step_order)
);

-- Indexes
CREATE INDEX idx_workflow_steps_automation_id ON automation.workflow_steps(automation_id);
CREATE INDEX idx_workflow_steps_order ON automation.workflow_steps(automation_id, step_order);
CREATE INDEX idx_workflow_steps_type ON automation.workflow_steps(step_type);
CREATE INDEX idx_workflow_steps_enabled ON automation.workflow_steps(enabled) WHERE enabled = true;

COMMENT ON TABLE automation.workflow_steps IS
'Sequential steps that compose an automation workflow.
Each step can be an action (tool call, API request) or a control (condition, loop).';

-- NOTE: Ces contraintes et commentaires ont été corrigés par la migration 031
COMMENT ON COLUMN automation.workflow_steps.step_type IS
'Type principal du step (2 catégories):
- action: Exécute une action (MCP tool, agent IA, tool interne)
- control: Contrôle le flux d''exécution (condition, loop, delay)

Cette architecture simple permet d''ajouter de nouveaux step_subtype sans modifier la contrainte.
[Corrigé par migration 031]';

COMMENT ON COLUMN automation.workflow_steps.step_subtype IS
'Sous-type spécifique pour les détails d''implémentation:

Pour step_type="action":
  - mcp_call: Appel d''un outil MCP externe
  - ai_action: Appel d''un agent IA (version simplifiée)
  - ai_agent: Appel d''un agent IA (version complète)
  - internal_tool: Appel d''un outil interne (search_resources, etc.)

Pour step_type="control":
  - condition: Branchement conditionnel (if/else, switch)
  - loop: Boucle (for_each, while, until)
  - delay: Pause temporelle

Cette liste peut être étendue sans modifier la base de données.
[Corrigé par migration 031]';

COMMENT ON COLUMN automation.workflow_steps.config IS
'Configuration for the step in JSONB format.
Structure varies based on step_type and step_subtype.';

COMMENT ON COLUMN automation.workflow_steps.run_condition IS
'Optional JavaScript expression that determines if step should run.
Example: "previous.status === ''success'' && data.count > 0"';

-- ============================================================================
-- STEP 4: Table triggers (Automation triggers)
-- ============================================================================

CREATE TABLE automation.triggers (
  id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('trigger'),
  automation_id TEXT NOT NULL REFERENCES automation.automations(id) ON DELETE CASCADE,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('cron', 'webhook', 'date', 'event', 'manual')),
  config JSONB DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_triggers_automation_id ON automation.triggers(automation_id);
CREATE INDEX idx_triggers_type ON automation.triggers(trigger_type);
CREATE INDEX idx_triggers_enabled ON automation.triggers(enabled) WHERE enabled = true;

COMMENT ON TABLE automation.triggers IS
'Triggers that can start an automation execution.
Each automation can have multiple triggers of different types.';

COMMENT ON COLUMN automation.triggers.trigger_type IS
'Trigger type:
- cron: Scheduled execution (config: {cron_expression})
- webhook: HTTP webhook endpoint (config: {url, secret})
- date: One-time execution at specific date (config: {execute_at})
- event: System event listener (config: {event_name, filters})
- manual: User-initiated execution only';

COMMENT ON COLUMN automation.triggers.config IS
'Configuration for the trigger in JSONB format.
Structure varies based on trigger_type.
Examples:
- cron: {"cron_expression": "0 9 * * 1-5"}
- webhook: {"url": "/webhook/abc123", "secret": "..."}
- date: {"execute_at": "2025-12-31T23:59:59Z"}
- event: {"event_name": "chat.message.created", "filters": {...}}';

-- ============================================================================
-- STEP 5: Table executions (Automation execution history)
-- ============================================================================

CREATE TABLE automation.executions (
  id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('exec'),
  automation_id TEXT NOT NULL REFERENCES automation.automations(id) ON DELETE CASCADE,
  trigger_id TEXT REFERENCES automation.triggers(id) ON DELETE SET NULL,
  user_id TEXT NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'cancelled')),
  input_params JSONB DEFAULT '{}',
  result JSONB,
  error TEXT,
  error_step_id TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_executions_automation_id ON automation.executions(automation_id);
CREATE INDEX idx_executions_trigger_id ON automation.executions(trigger_id);
CREATE INDEX idx_executions_user_id ON automation.executions(user_id);
CREATE INDEX idx_executions_status ON automation.executions(status);
CREATE INDEX idx_executions_started_at ON automation.executions(started_at DESC);

COMMENT ON TABLE automation.executions IS
'Tracks each execution of an automation.
Stores input parameters, final result, and execution status.';

COMMENT ON COLUMN automation.executions.status IS
'Execution status:
- running: Currently executing
- success: Completed successfully
- failed: Failed with error
- cancelled: Cancelled by user or system';

COMMENT ON COLUMN automation.executions.error_step_id IS
'ID of the workflow step that caused the error (if failed).';

-- ============================================================================
-- STEP 6: Table execution_step_logs (Partitioned detailed step logs)
-- ============================================================================

CREATE TABLE automation.execution_step_logs (
  id TEXT DEFAULT core.generate_prefixed_id('log'),
  execution_id TEXT NOT NULL,
  step_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'skipped')),
  result JSONB,
  error TEXT,
  duration_ms INTEGER,
  executed_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (executed_at);

-- Create partitions for Q1 2026 (3 months)
CREATE TABLE automation.execution_step_logs_2026_01 PARTITION OF automation.execution_step_logs
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE automation.execution_step_logs_2026_02 PARTITION OF automation.execution_step_logs
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE automation.execution_step_logs_2026_03 PARTITION OF automation.execution_step_logs
  FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Indexes on each partition (created automatically via parent table indexes)
CREATE INDEX idx_execution_step_logs_execution_id ON automation.execution_step_logs(execution_id);
CREATE INDEX idx_execution_step_logs_step_id ON automation.execution_step_logs(step_id);
CREATE INDEX idx_execution_step_logs_status ON automation.execution_step_logs(status);
CREATE INDEX idx_execution_step_logs_executed_at ON automation.execution_step_logs(executed_at DESC);

COMMENT ON TABLE automation.execution_step_logs IS
'Detailed logs for each workflow step execution.
Partitioned by executed_at for better performance on large datasets.
New partitions should be created monthly via maintenance job.';

COMMENT ON COLUMN automation.execution_step_logs.status IS
'Step execution status:
- running: Currently executing
- success: Completed successfully
- failed: Failed with error
- skipped: Skipped due to run_condition';

COMMENT ON COLUMN automation.execution_step_logs.duration_ms IS
'Execution duration in milliseconds.';

-- ============================================================================
-- STEP 7: Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify automation schema exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'automation') THEN
        RAISE EXCEPTION 'Schema automation does not exist';
    END IF;

    -- Verify all tables exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'automations') THEN
        RAISE EXCEPTION 'Table automation.automations does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'workflow_steps') THEN
        RAISE EXCEPTION 'Table automation.workflow_steps does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'triggers') THEN
        RAISE EXCEPTION 'Table automation.triggers does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'executions') THEN
        RAISE EXCEPTION 'Table automation.executions does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'execution_step_logs') THEN
        RAISE EXCEPTION 'Table automation.execution_step_logs does not exist';
    END IF;

    -- Verify partitions exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'execution_step_logs_2026_01') THEN
        RAISE EXCEPTION 'Partition automation.execution_step_logs_2026_01 does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'execution_step_logs_2026_02') THEN
        RAISE EXCEPTION 'Partition automation.execution_step_logs_2026_02 does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'automation' AND table_name = 'execution_step_logs_2026_03') THEN
        RAISE EXCEPTION 'Partition automation.execution_step_logs_2026_03 does not exist';
    END IF;

    RAISE NOTICE 'Automation schema created successfully with 5 tables and 3 partitions';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Create new partitions monthly before the month starts
-- 2. Example partition creation:
--    CREATE TABLE automation.execution_step_logs_2025_04 PARTITION OF automation.execution_step_logs
--      FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
-- 3. Old partitions can be dropped or archived after retention period
-- 4. Consider pg_cron or similar for automatic partition management
-- ============================================================================
