-- Migration 005 : Table user_providers pour la gestion multi-tenant des providers LLM
-- Date: 2025-11-26
-- Description: Permet à chaque utilisateur d'activer ses propres providers avec ses propres clés API

-- ============================================================================
-- TABLE : user_providers (Association user ↔ service ↔ api_key)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_providers (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('upr'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  service_id TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  api_key_id TEXT REFERENCES api_keys(id) ON DELETE SET NULL,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, service_id)
);

-- ============================================================================
-- INDEX : Optimisation des requêtes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_providers_user_id ON user_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_providers_service_id ON user_providers(service_id);
CREATE INDEX IF NOT EXISTS idx_user_providers_api_key_id ON user_providers(api_key_id);
CREATE INDEX IF NOT EXISTS idx_user_providers_enabled ON user_providers(enabled);

-- Index composite pour les requêtes fréquentes (user + enabled)
CREATE INDEX IF NOT EXISTS idx_user_providers_user_enabled ON user_providers(user_id, enabled);

-- ============================================================================
-- FIN DE LA MIGRATION 005
-- ============================================================================
