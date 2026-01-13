-- ============================================================================
-- MIGRATION 007 : Ajout du système de status pour les serveurs MCP
-- ============================================================================

-- Supprimer l'ancienne colonne api_key (non utilisée, BDD vide)
ALTER TABLE servers DROP COLUMN IF EXISTS api_key;

-- Supprimer l'ancienne contrainte auth_type pour la recréer
ALTER TABLE servers DROP CONSTRAINT IF EXISTS servers_auth_type_check;

-- Ajouter la nouvelle contrainte avec 'none'
ALTER TABLE servers ADD CONSTRAINT servers_auth_type_check
  CHECK (auth_type IN ('api-key', 'oauth', 'none'));

-- Ajouter les nouvelles colonnes pour le suivi du status
ALTER TABLE servers
  ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'active', 'failed', 'unreachable')),
  ADD COLUMN status_message TEXT,
  ADD COLUMN last_health_check TIMESTAMPTZ,
  ADD COLUMN api_key_id TEXT REFERENCES api_keys(id) ON DELETE SET NULL;

-- Index pour les requêtes fréquentes
CREATE INDEX idx_servers_status ON servers(status);
CREATE INDEX idx_servers_api_key_id ON servers(api_key_id);

-- ============================================================================
-- FIN DE LA MIGRATION 007
-- ============================================================================
