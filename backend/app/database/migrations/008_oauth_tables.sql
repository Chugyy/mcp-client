-- ============================================================================
-- MIGRATION 008 : Tables OAuth 2.1 pour MCP
-- ============================================================================

-- Table pour stocker les sessions OAuth (state, PKCE verifier)
CREATE TABLE oauth_sessions (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('oas'),
  server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  state TEXT NOT NULL UNIQUE,
  code_verifier TEXT NOT NULL,
  code_challenge TEXT NOT NULL,
  redirect_uri TEXT NOT NULL,
  scope TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '10 minutes'
);

-- Table pour stocker les tokens OAuth
CREATE TABLE oauth_tokens (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('oat'),
  server_id TEXT NOT NULL UNIQUE REFERENCES servers(id) ON DELETE CASCADE,
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_type TEXT NOT NULL DEFAULT 'Bearer',
  expires_at TIMESTAMPTZ NOT NULL,
  scope TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour les requêtes fréquentes
CREATE INDEX idx_oauth_sessions_server_id ON oauth_sessions(server_id);
CREATE INDEX idx_oauth_sessions_state ON oauth_sessions(state);
CREATE INDEX idx_oauth_sessions_expires_at ON oauth_sessions(expires_at);
CREATE INDEX idx_oauth_tokens_server_id ON oauth_tokens(server_id);

-- Ajouter le status 'pending_authorization' pour les serveurs OAuth
ALTER TABLE servers DROP CONSTRAINT IF EXISTS servers_status_check;
ALTER TABLE servers ADD CONSTRAINT servers_status_check
  CHECK (status IN ('pending', 'pending_authorization', 'active', 'failed', 'unreachable'));

-- ============================================================================
-- FIN DE LA MIGRATION 008
-- ============================================================================
