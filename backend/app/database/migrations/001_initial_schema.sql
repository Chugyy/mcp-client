-- Migration initiale : Schéma complet de la base de données
-- Date: 2025-11-26
-- Description: Création de toutes les tables avec IDs préfixés et contraintes

-- ============================================================================
-- NETTOYAGE : Suppression des tables existantes (ordre inverse des dépendances)
-- ============================================================================

DROP TABLE IF EXISTS configurations CASCADE;
DROP TABLE IF EXISTS tools CASCADE;
DROP TABLE IF EXISTS servers CASCADE;
DROP TABLE IF EXISTS resources CASCADE;
DROP TABLE IF EXISTS validations CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS chats CASCADE;
DROP TABLE IF EXISTS memberships CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS uploads CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS reset_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP FUNCTION IF EXISTS generate_prefixed_id(TEXT) CASCADE;

-- ============================================================================
-- FONCTION : Génération d'IDs préfixés
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_prefixed_id(prefix TEXT)
RETURNS TEXT AS $$
DECLARE
  chars TEXT := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  result TEXT := '';
  i INTEGER;
BEGIN
  FOR i IN 1..6 LOOP
    result := result || substr(chars, floor(random() * length(chars) + 1)::int, 1);
  END LOOP;
  RETURN prefix || '_' || result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TABLE : users (Utilisateurs du système)
-- ============================================================================

CREATE TABLE users (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('usr'),
  email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  name TEXT NOT NULL,
  preferences JSONB DEFAULT '{"theme":"system","language":"fr"}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- TABLE : reset_tokens (Tokens de réinitialisation de mot de passe)
-- ============================================================================

CREATE TABLE reset_tokens (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('rst'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reset_tokens_token ON reset_tokens(token);
CREATE INDEX idx_reset_tokens_user_id ON reset_tokens(user_id);

-- ============================================================================
-- TABLE : agents (Agents IA)
-- ============================================================================

CREATE TABLE agents (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('agt'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  system_prompt TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  resource_ids TEXT[] DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agents_user_id ON agents(user_id);
CREATE INDEX idx_agents_enabled ON agents(enabled);
CREATE INDEX idx_agents_resource_ids ON agents USING GIN(resource_ids);

-- ============================================================================
-- TABLE : uploads (Fichiers uploadés)
-- ============================================================================

CREATE TABLE uploads (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('upl'),
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  agent_id TEXT REFERENCES agents(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('avatar', 'document')),
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT,
  mime_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK (
    (user_id IS NOT NULL AND agent_id IS NULL) OR
    (user_id IS NULL AND agent_id IS NOT NULL)
  )
);

CREATE INDEX idx_uploads_user_id ON uploads(user_id);
CREATE INDEX idx_uploads_agent_id ON uploads(agent_id);
CREATE INDEX idx_uploads_type ON uploads(type);

-- ============================================================================
-- TABLE : teams (Équipes d'agents)
-- ============================================================================

CREATE TABLE teams (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('tem'),
  name TEXT NOT NULL,
  description TEXT,
  system_prompt TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_teams_enabled ON teams(enabled);

-- ============================================================================
-- TABLE : memberships (Appartenance agent-équipe)
-- ============================================================================

CREATE TABLE memberships (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('mbr'),
  team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(team_id, agent_id)
);

CREATE INDEX idx_memberships_team_id ON memberships(team_id);
CREATE INDEX idx_memberships_agent_id ON memberships(agent_id);

-- ============================================================================
-- TABLE : chats (Conversations)
-- ============================================================================

CREATE TABLE chats (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('cht'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
  team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK (
    (agent_id IS NOT NULL AND team_id IS NULL) OR
    (agent_id IS NULL AND team_id IS NOT NULL)
  )
);

CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_chats_agent_id ON chats(agent_id);
CREATE INDEX idx_chats_team_id ON chats(team_id);

-- ============================================================================
-- TABLE : messages (Messages de conversation)
-- ============================================================================

CREATE TABLE messages (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('msg'),
  chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- ============================================================================
-- TABLE : validations (Demandes de validation)
-- ============================================================================

CREATE TABLE validations (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('val'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  source TEXT NOT NULL,
  process TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'validated', 'cancelled', 'feedback')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validations_user_id ON validations(user_id);
CREATE INDEX idx_validations_status ON validations(status);
CREATE INDEX idx_validations_agent_id ON validations(agent_id);

-- ============================================================================
-- TABLE : resources (Ressources externes)
-- ============================================================================

CREATE TABLE resources (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('res'),
  name TEXT NOT NULL,
  description TEXT,
  type TEXT NOT NULL CHECK (type IN ('google-drive', 'icloud', 'onedrive', 'dropbox', 'custom')),
  config JSONB NOT NULL,
  methods TEXT[] DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_enabled ON resources(enabled);

-- ============================================================================
-- TABLE : servers (Serveurs MCP)
-- ============================================================================

CREATE TABLE servers (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('srv'),
  name TEXT NOT NULL,
  description TEXT,
  url TEXT NOT NULL,
  auth_type TEXT NOT NULL CHECK (auth_type IN ('api-key', 'oauth')),
  api_key TEXT,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_servers_enabled ON servers(enabled);

-- ============================================================================
-- TABLE : tools (Outils fournis par les serveurs)
-- ============================================================================

CREATE TABLE tools (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('tol'),
  server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tools_server_id ON tools(server_id);

-- ============================================================================
-- TABLE : configurations (Configurations agent-serveur-outil)
-- ============================================================================

CREATE TABLE configurations (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('cfg'),
  agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  tool_id TEXT REFERENCES tools(id) ON DELETE CASCADE,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agent_id, server_id, tool_id)
);

CREATE INDEX idx_configurations_agent_id ON configurations(agent_id);
CREATE INDEX idx_configurations_server_id ON configurations(server_id);

-- ============================================================================
-- FIN DE LA MIGRATION
-- ============================================================================
