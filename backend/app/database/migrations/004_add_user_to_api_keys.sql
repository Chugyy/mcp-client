-- Migration 004 : Ajout de user_id à la table api_keys
-- Date: 2025-11-26
-- Description: Lie chaque clé API à un utilisateur spécifique pour isolation multi-tenant

-- ============================================================================
-- MODIFICATION : api_keys (Ajout de user_id)
-- ============================================================================

ALTER TABLE api_keys
  ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- ============================================================================
-- Note: Les clés API existantes sans user_id devront être migrées manuellement
-- ou supprimées avant de rendre la colonne NOT NULL
-- ============================================================================

-- Pour rendre la colonne obligatoire après migration des données:
-- ALTER TABLE api_keys ALTER COLUMN user_id SET NOT NULL;

-- ============================================================================
-- FIN DE LA MIGRATION 004
-- ============================================================================
