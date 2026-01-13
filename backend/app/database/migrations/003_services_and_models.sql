-- Migration 003 : Architecture centralisée des services externes
-- Date: 2025-11-26
-- Description: Création des tables services et models pour gérer tous les services externes (LLM, MCP, Resources)

-- ============================================================================
-- TABLE : services (Services externes - LLM, MCP, Resources)
-- ============================================================================

CREATE TABLE IF NOT EXISTS services (
    id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('svc'),
    name TEXT NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('openai', 'anthropic', 'mcp', 'resource', 'custom')),
    description TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deprecated')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_services_provider ON services(provider);
CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);

-- ============================================================================
-- TABLE : models (Modèles LLM disponibles par service)
-- ============================================================================

CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('mdl'),
    service_id TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    display_name TEXT,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service_id, model_name)
);

CREATE INDEX IF NOT EXISTS idx_models_service_id ON models(service_id);
CREATE INDEX IF NOT EXISTS idx_models_enabled ON models(enabled);
CREATE INDEX IF NOT EXISTS idx_models_model_name ON models(model_name);

-- ============================================================================
-- MODIFICATION : api_keys (Ajout de service_id pour lier à un service)
-- ============================================================================

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS service_id TEXT REFERENCES services(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_api_keys_service_id ON api_keys(service_id);

-- ============================================================================
-- MODIFICATION : resources (Remplacer api_key_id par service_id)
-- ============================================================================

ALTER TABLE resources ADD COLUMN IF NOT EXISTS service_id TEXT REFERENCES services(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_resources_service_id ON resources(service_id);

-- Note: La colonne api_key_id sera migrée puis supprimée manuellement après migration des données

-- ============================================================================
-- MODIFICATION : servers (Remplacer api_key et api_key_id par service_id)
-- ============================================================================

ALTER TABLE servers ADD COLUMN IF NOT EXISTS service_id TEXT REFERENCES services(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_servers_service_id ON servers(service_id);

-- Note: Les colonnes api_key et api_key_id seront supprimées manuellement après migration des données
-- Pour raisons de sécurité: supprimer api_key (plain text) dès que possible

-- ============================================================================
-- FIN DE LA MIGRATION 003
-- ============================================================================
