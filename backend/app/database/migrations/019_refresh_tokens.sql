-- Migration 019 : Refresh Tokens
-- Date: 2025-11-30
-- Description: Création de la table refresh_tokens pour le système d'authentification avec refresh token

-- ============================================================================
-- TABLE : refresh_tokens
-- ============================================================================

CREATE TABLE IF NOT EXISTS core.refresh_tokens (
    id TEXT PRIMARY KEY DEFAULT core.generate_prefixed_id('rt'),
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Contraintes
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id)
        REFERENCES core.users(id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEX : Optimisation des requêtes
-- ============================================================================

-- Index sur user_id pour récupérer tous les tokens d'un utilisateur
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON core.refresh_tokens(user_id);

-- Index sur token_hash pour les lookups (déjà UNIQUE donc automatiquement indexé)
-- Mais on le crée explicitement pour la clarté
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON core.refresh_tokens(token_hash);

-- Index sur expires_at pour les requêtes de nettoyage
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON core.refresh_tokens(expires_at);

-- Index composite pour les requêtes fréquentes (token valide et non révoqué)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_valid ON core.refresh_tokens(token_hash, revoked, expires_at);

-- ============================================================================
-- TRIGGER : updated_at automatique
-- ============================================================================

CREATE OR REPLACE FUNCTION core.update_refresh_tokens_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_refresh_tokens_updated_at
    BEFORE UPDATE ON core.refresh_tokens
    FOR EACH ROW
    EXECUTE FUNCTION core.update_refresh_tokens_updated_at();

-- ============================================================================
-- COMMENTAIRES : Documentation
-- ============================================================================

COMMENT ON TABLE core.refresh_tokens IS 'Stockage des refresh tokens pour l''authentification JWT';
COMMENT ON COLUMN core.refresh_tokens.id IS 'Identifiant unique du refresh token (rt_xxx)';
COMMENT ON COLUMN core.refresh_tokens.user_id IS 'Référence vers l''utilisateur';
COMMENT ON COLUMN core.refresh_tokens.token_hash IS 'Hash SHA256 du refresh token (jamais en clair)';
COMMENT ON COLUMN core.refresh_tokens.expires_at IS 'Date d''expiration du token (7 jours)';
COMMENT ON COLUMN core.refresh_tokens.revoked IS 'Indicateur de révocation (logout)';
COMMENT ON COLUMN core.refresh_tokens.created_at IS 'Date de création';
COMMENT ON COLUMN core.refresh_tokens.updated_at IS 'Date de dernière modification';
