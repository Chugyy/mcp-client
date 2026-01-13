-- ============================================================================
-- Migration 022: Add input_schema to tools table
-- ============================================================================
-- Description:
--   Adds input_schema JSONB column to store MCP tool schemas
--   This allows proper validation of tool inputs and schema passing to LLMs
-- ============================================================================

BEGIN;

-- Add input_schema column to tools table
ALTER TABLE tools
ADD COLUMN input_schema JSONB DEFAULT '{
  "type": "object",
  "properties": {},
  "required": []
}'::jsonb;

-- Create index on input_schema for performance
CREATE INDEX idx_tools_input_schema ON tools USING GIN(input_schema);

-- Add comment
COMMENT ON COLUMN tools.input_schema IS 'JSON Schema for tool input parameters (MCP standard)';

COMMIT;

-- ============================================================================
-- Notes:
-- - Default schema is an empty object schema (valid JSON Schema)
-- - Existing tools will get the default empty schema
-- - New tools should populate this from MCP server response
-- ============================================================================
