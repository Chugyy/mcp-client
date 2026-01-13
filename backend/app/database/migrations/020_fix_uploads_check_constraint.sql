-- Migration 020: Fix uploads table CHECK constraint to include resource_id
-- ============================================================================
-- Problème: La contrainte CHECK actuelle n'autorise que user_id XOR agent_id,
--           mais ne prend pas en compte resource_id
-- Solution: Modifier la contrainte pour autoriser exactement UN des trois champs

-- 1. Supprimer l'ancienne contrainte
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_check;

-- 2. Ajouter la nouvelle contrainte qui permet user_id XOR agent_id XOR resource_id
ALTER TABLE uploads ADD CONSTRAINT uploads_check CHECK (
  (
    (user_id IS NOT NULL)::int +
    (agent_id IS NOT NULL)::int +
    (resource_id IS NOT NULL)::int
  ) = 1
);

-- Note: Cette contrainte garantit qu'exactement UN des trois champs est rempli
-- Exemples valides:
--   - user_id='usr_xxx', agent_id=NULL, resource_id=NULL  ✓
--   - user_id=NULL, agent_id='agt_xxx', resource_id=NULL  ✓
--   - user_id=NULL, agent_id=NULL, resource_id='res_xxx'  ✓
-- Exemples invalides:
--   - user_id='usr_xxx', agent_id='agt_xxx', resource_id=NULL  ✗
--   - user_id=NULL, agent_id=NULL, resource_id=NULL  ✗

-- ============================================================================
-- Rollback (si nécessaire) :
-- ============================================================================
-- ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_check;
-- ALTER TABLE uploads ADD CONSTRAINT uploads_check CHECK (
--   (user_id IS NOT NULL AND agent_id IS NULL) OR
--   (user_id IS NULL AND agent_id IS NOT NULL)
-- );
