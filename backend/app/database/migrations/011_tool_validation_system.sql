-- ============================================================================
-- Migration 011: Système de validation des tool calls
-- ============================================================================
-- Description:
--   - Ajoute permission_level aux users (full_auto, validation_required, no_tools)
--   - Ajoute colonnes liées aux tools dans validations
--   - Modifie contrainte messages pour supporter role='tool_call'
--   - Crée table logs générique pour historique et cache
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. TABLE USERS : Ajout permission_level
-- ============================================================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS permission_level TEXT
DEFAULT 'validation_required'
CHECK (permission_level IN ('full_auto', 'validation_required', 'no_tools'));

COMMENT ON COLUMN users.permission_level IS
'Niveau de permission pour les tool calls:
- full_auto: Tous les tools s''exécutent sans validation
- validation_required: Demande validation avant chaque tool call (avec cache)
- no_tools: Désactive complètement le tool calling';

-- ============================================================================
-- 2. TABLE VALIDATIONS : Ajout colonnes pour tool calls
-- ============================================================================

ALTER TABLE validations
ADD COLUMN IF NOT EXISTS chat_id TEXT REFERENCES chats(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS tool_name TEXT,
ADD COLUMN IF NOT EXISTS server_id TEXT REFERENCES servers(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS tool_args JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS tool_result JSONB,
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '15 days');

-- Modifier les statuts acceptés
ALTER TABLE validations DROP CONSTRAINT IF EXISTS validations_status_check;
ALTER TABLE validations ADD CONSTRAINT validations_status_check
CHECK (status IN ('pending', 'approved', 'rejected', 'feedback', 'cancelled'));

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_validations_chat_id ON validations(chat_id);
CREATE INDEX IF NOT EXISTS idx_validations_expires_at ON validations(expires_at) WHERE status = 'pending';

COMMENT ON TABLE validations IS
'Stocke les demandes de validation pour les tool calls.
Chaque validation représente une demande d''autorisation avant exécution d''un outil MCP.';

-- ============================================================================
-- 3. TABLE MESSAGES : Support du role 'tool_call'
-- ============================================================================

-- Modifier la contrainte pour ajouter 'tool_call'
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_role_check;
ALTER TABLE messages ADD CONSTRAINT messages_role_check
CHECK (role IN ('user', 'assistant', 'tool_call'));

COMMENT ON COLUMN messages.role IS
'Rôle du message:
- user: Message de l''utilisateur
- assistant: Réponse du LLM
- tool_call: Étape d''exécution d''un outil (validation_requested, executing, completed, rejected, feedback_received)';

COMMENT ON COLUMN messages.metadata IS
'Métadonnées au format JSONB.
Pour tool_call: {step, validation_id, tool_name, server_id, arguments, status, result}';

-- ============================================================================
-- 4. TABLE LOGS : Historique générique et cache d'autorisations
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('log'),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
  chat_id TEXT REFERENCES chats(id) ON DELETE SET NULL,

  -- Type de log
  type TEXT NOT NULL CHECK (type IN ('tool_call', 'validation', 'stream_stop', 'error')),

  -- Données flexibles selon le type
  data JSONB NOT NULL,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX idx_logs_chat_id ON logs(chat_id);
CREATE INDEX idx_logs_type ON logs(type);
CREATE INDEX idx_logs_user_agent ON logs(user_id, agent_id);

-- Index spécifique pour le cache (always_allow=true)
CREATE INDEX idx_logs_tool_cache ON logs(user_id, agent_id, type, ((data->>'tool_name')), ((data->>'server_id')))
WHERE type = 'tool_call' AND (data->>'always_allow')::boolean = true;

COMMENT ON TABLE logs IS
'Table générique pour tous les logs système.
Supporte: tool_call (historique + cache), validation (actions), stream_stop, error.';

COMMENT ON COLUMN logs.type IS
'Type de log:
- tool_call: Exécution d''un outil (avec cache si data.always_allow=true)
- validation: Action de validation (approved, rejected, feedback)
- stream_stop: Arrêt d''un stream par l''utilisateur
- error: Erreur système';

COMMENT ON COLUMN logs.data IS
'Données au format JSONB, structure selon le type:
tool_call: {tool_name, server_id, args, result, status, always_allow}
validation: {validation_id, action, tool_name}
stream_stop: {reason}
error: {message, stack_trace}';

COMMIT;

-- ============================================================================
-- FIN DE LA MIGRATION
-- ============================================================================
-- Exemples de requêtes:
--
-- Vérifier le cache d'autorisation pour un tool:
-- SELECT * FROM logs
-- WHERE type = 'tool_call'
--   AND user_id = $1
--   AND agent_id = $2
--   AND data->>'tool_name' = $3
--   AND data->>'server_id' = $4
--   AND (data->>'always_allow')::boolean = true
-- LIMIT 1;
--
-- Lister l'historique des tool calls d'un chat:
-- SELECT * FROM logs
-- WHERE chat_id = $1
--   AND type = 'tool_call'
-- ORDER BY created_at DESC;
--
-- Nettoyer les validations expirées (tâche CRON):
-- UPDATE validations
-- SET status = 'cancelled'
-- WHERE status = 'pending'
--   AND expires_at < NOW();
-- ============================================================================
