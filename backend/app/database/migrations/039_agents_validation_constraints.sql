-- ============================================================================
-- Migration 039: Agents Validation Constraints
-- ============================================================================
-- Description: Add validation constraints and performance indexes for agents
-- Date: 2025-12-10
-- ============================================================================

BEGIN;

-- ===== CONTRAINTES D'UNICITÉ =====

-- Contrainte: Un utilisateur ne peut avoir qu'un agent avec un nom donné
-- Note: Utilise DO $$ pour idempotence (ne pas échouer si contrainte existe déjà)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agents_name_user_unique'
    ) THEN
        ALTER TABLE agents ADD CONSTRAINT agents_name_user_unique
            UNIQUE(name, user_id);
    END IF;
END $$;

-- ===== INDEX DE PERFORMANCE =====

-- Index composite pour requêtes fréquentes (list agents by user + enabled)
-- Utilisé par: GET /agents?enabled=true
CREATE INDEX IF NOT EXISTS idx_agents_user_enabled
ON agents(user_id, enabled);

-- Index GIN pour recherche full-text sur tags
-- Utilisé par: Recherche d'agents par tags
CREATE INDEX IF NOT EXISTS idx_agents_tags
ON agents USING GIN(tags);

-- Index pour comptage rapide d'agents par user (quota)
-- Utilisé par: validate_agent_quota()
CREATE INDEX IF NOT EXISTS idx_agents_user_count
ON agents(user_id);

-- ===== COMMENTAIRES =====

COMMENT ON CONSTRAINT agents_name_user_unique ON agents IS
'Chaque utilisateur ne peut avoir qu''un seul agent avec un nom donné.
Cela garantit l''unicité des noms d''agents au sein de l''espace de travail d''un utilisateur.';

COMMENT ON INDEX idx_agents_user_enabled IS
'Index de performance pour requêtes combinant user_id et enabled (ex: liste agents actifs)';

COMMENT ON INDEX idx_agents_tags IS
'Index GIN pour recherche full-text performante sur les tags d''agents';

COMMENT ON INDEX idx_agents_user_count IS
'Index de performance pour comptage rapide d''agents par utilisateur (validation quota)';

-- ===== VÉRIFICATION =====

DO $$
BEGIN
    -- Vérifier que la contrainte existe
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agents_name_user_unique'
    ) THEN
        RAISE EXCEPTION 'Constraint agents_name_user_unique was not created';
    END IF;

    -- Vérifier que les index existent
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_agents_user_enabled'
    ) THEN
        RAISE EXCEPTION 'Index idx_agents_user_enabled was not created';
    END IF;

    RAISE NOTICE 'Migration 039 completed successfully: agents validation constraints added';
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Migration idempotente : peut être exécutée plusieurs fois sans erreur
-- 2. Contrainte UNIQUE(name, user_id) empêche les doublons au niveau DB
-- 3. Index stratégiques pour optimiser les requêtes fréquentes
-- 4. CASCADE DELETE déjà géré par migration 025 (chats, configurations, uploads)
-- ============================================================================
