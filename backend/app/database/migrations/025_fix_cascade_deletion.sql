-- ============================================================================
-- Migration 025: Fix cascade deletion for agents/teams
-- ============================================================================
-- Description: Change ON DELETE SET NULL to CASCADE to avoid orphaned chats
-- Date: 2025-12-02
-- ============================================================================

BEGIN;

-- 1. Fix chats.agent_id: SET NULL → CASCADE
ALTER TABLE chats DROP CONSTRAINT IF EXISTS chats_agent_id_fkey;
ALTER TABLE chats ADD CONSTRAINT chats_agent_id_fkey
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

-- 2. Fix chats.team_id: SET NULL → CASCADE
ALTER TABLE chats DROP CONSTRAINT IF EXISTS chats_team_id_fkey;
ALTER TABLE chats ADD CONSTRAINT chats_team_id_fkey
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;

-- 3. Fix validations.agent_id: SET NULL → CASCADE (for consistency)
ALTER TABLE validations DROP CONSTRAINT IF EXISTS validations_agent_id_fkey;
ALTER TABLE validations ADD CONSTRAINT validations_agent_id_fkey
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

COMMIT;

-- ============================================================================
-- Notes:
-- - Chats orphelins après suppression d'agent sont maintenant automatiquement supprimés
-- - La contrainte chats_initialization_check reste valide en permanence
-- - Les validations liées à un agent supprimé sont également supprimées
-- ============================================================================
