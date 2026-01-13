-- ============================================================================
-- Migration 009: Refactorisation de configurations en système générique
-- ============================================================================
-- Description:
--   - Transforme configurations en système générique (entity_type + entity_id)
--   - Supprime resource_ids de agents
--   - Permet d'assigner serveurs MCP, ressources, et futures entités
-- ============================================================================

BEGIN;

-- 1. Supprimer la table configurations existante
DROP TABLE IF EXISTS configurations CASCADE;

-- 2. Créer configurations avec la nouvelle structure générique
CREATE TABLE configurations (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('cfg'),
  agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('server', 'resource')),
  entity_id TEXT NOT NULL,
  config_data JSONB DEFAULT '{}'::jsonb,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agent_id, entity_type, entity_id)
);

-- 3. Index pour performance
CREATE INDEX idx_configurations_agent_id ON configurations(agent_id);
CREATE INDEX idx_configurations_entity_type ON configurations(entity_type);
CREATE INDEX idx_configurations_entity_id ON configurations(entity_id);
CREATE INDEX idx_configurations_config_data ON configurations USING GIN(config_data);

-- 4. Supprimer resource_ids de agents
ALTER TABLE agents DROP COLUMN IF EXISTS resource_ids;

COMMIT;

-- ============================================================================
-- Notes:
-- - Les anciennes configurations sont supprimées (BDD de dev)
-- - tool_id est maintenant dans config_data.tool_id (JSONB)
-- - entity_type peut être 'server' ou 'resource' (extensible)
-- - resource_ids a été retiré de agents
-- ============================================================================
