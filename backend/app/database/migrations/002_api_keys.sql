-- Migration 002 : Système centralisé de gestion des clés API
-- Date: 2025-11-26
-- Description: Création de la table api_keys et ajout des colonnes api_key_id dans servers et resources

-- ============================================================================
-- TABLE : api_keys (Clés API centralisées et chiffrées)
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('key'),
  encrypted_value TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at);

-- ============================================================================
-- MODIFICATION : servers (Ajout de la référence vers api_keys)
-- ============================================================================

ALTER TABLE servers ADD COLUMN IF NOT EXISTS api_key_id TEXT REFERENCES api_keys(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_servers_api_key_id ON servers(api_key_id);

-- ============================================================================
-- MODIFICATION : resources (Ajout de la référence vers api_keys)
-- ============================================================================

ALTER TABLE resources ADD COLUMN IF NOT EXISTS api_key_id TEXT REFERENCES api_keys(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_resources_api_key_id ON resources(api_key_id);

-- ============================================================================
-- FIN DE LA MIGRATION 002
-- ============================================================================
