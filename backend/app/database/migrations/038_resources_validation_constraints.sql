-- Migration 038: Contraintes de validation et index pour Resources
-- Conforme au pattern MCP (ARCHITECTURE_VALIDATION.md)

-- ===== CONTRAINTES D'UNICITÉ =====

-- Contrainte d'unicité (name, user_id) pour les ressources
-- Empêche les doublons de nom par utilisateur
ALTER TABLE resources
ADD CONSTRAINT resources_name_user_unique
UNIQUE(name, user_id);

-- ===== INDEX DE PERFORMANCE =====

-- Index pour requêtes sur (user_id, enabled)
-- Utilisé par list_resources_by_user avec enabled_only=true
CREATE INDEX IF NOT EXISTS idx_resources_user_enabled
ON resources(user_id, enabled);

-- Index pour requêtes sur status
-- Utilisé pour filtrer par statut (pending, processing, ready, error)
CREATE INDEX IF NOT EXISTS idx_resources_status
ON resources(status);

-- Index pour requêtes sur indexed_at
-- Utilisé pour déterminer ressources récemment indexées
CREATE INDEX IF NOT EXISTS idx_resources_indexed_at
ON resources(indexed_at);

-- Index pour requêtes sur is_system
-- Utilisé pour protéger ressources système
CREATE INDEX IF NOT EXISTS idx_resources_is_system
ON resources(is_system);

-- ===== COMMENTAIRES =====

COMMENT ON CONSTRAINT resources_name_user_unique ON resources IS
'Garantit l''unicité du nom de ressource par utilisateur';

COMMENT ON INDEX idx_resources_user_enabled IS
'Index de performance pour list_resources_by_user(enabled_only=true)';

COMMENT ON INDEX idx_resources_status IS
'Index de performance pour filtrage par statut RAG';

COMMENT ON INDEX idx_resources_indexed_at IS
'Index de performance pour requêtes temporelles sur indexation';

COMMENT ON INDEX idx_resources_is_system IS
'Index de performance pour protection ressources système';
