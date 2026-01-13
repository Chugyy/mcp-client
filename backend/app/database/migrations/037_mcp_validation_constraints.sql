-- Migration 037: Contraintes de validation et index pour MCP
-- Ajoute contraintes d'unicité, index de performance, et standards de validation

-- ===== CONTRAINTES D'UNICITÉ =====

-- Contrainte d'unicité (name, user_id) pour les serveurs
-- Empêche les doublons de nom par utilisateur
ALTER TABLE servers
ADD CONSTRAINT servers_name_user_unique
UNIQUE(name, user_id);

-- ===== INDEX DE PERFORMANCE =====

-- Index pour requêtes sur (user_id, enabled)
-- Utilisé par list_servers_by_user avec enabled_only=true
CREATE INDEX IF NOT EXISTS idx_servers_user_enabled
ON servers(user_id, enabled);

-- Index pour requêtes sur last_health_check
-- Utilisé pour déterminer si un serveur est "stale"
CREATE INDEX IF NOT EXISTS idx_servers_last_health
ON servers(last_health_check);

-- Index pour requêtes sur status
-- Utilisé pour filtrer les serveurs par statut
CREATE INDEX IF NOT EXISTS idx_servers_status
ON servers(status);

-- Index pour requêtes sur type
-- Utilisé pour statistiques et requêtes par type de serveur
CREATE INDEX IF NOT EXISTS idx_servers_type
ON servers(type);

-- ===== INDEX POUR TOOLS =====

-- Index pour requêtes sur (server_id, enabled)
-- Utilisé par list_tools_by_server
CREATE INDEX IF NOT EXISTS idx_tools_server_enabled
ON tools(server_id, enabled);

-- Contrainte d'unicité (name, server_id) pour les tools
-- Empêche les doublons de tool par serveur
ALTER TABLE tools
ADD CONSTRAINT tools_name_server_unique
UNIQUE(name, server_id);

-- ===== INDEX POUR CONFIGURATIONS =====

-- Index pour requêtes sur (agent_id, entity_type)
-- Utilisé par list_configurations_by_agent
CREATE INDEX IF NOT EXISTS idx_configurations_agent_entity
ON configurations(agent_id, entity_type);

-- Contrainte d'unicité (agent_id, entity_type, entity_id)
-- Empêche les doublons de configuration
ALTER TABLE configurations
ADD CONSTRAINT configurations_agent_entity_unique
UNIQUE(agent_id, entity_type, entity_id);

-- ===== COMMENTAIRES =====

COMMENT ON CONSTRAINT servers_name_user_unique ON servers IS
'Garantit l''unicité du nom de serveur par utilisateur';

COMMENT ON CONSTRAINT tools_name_server_unique ON tools IS
'Garantit l''unicité du nom de tool par serveur';

COMMENT ON CONSTRAINT configurations_agent_entity_unique ON configurations IS
'Garantit qu''un agent ne peut avoir qu''une seule configuration par entité';

COMMENT ON INDEX idx_servers_user_enabled IS
'Index de performance pour list_servers_by_user(enabled_only=true)';

COMMENT ON INDEX idx_servers_last_health IS
'Index de performance pour détection de serveurs "stale"';
