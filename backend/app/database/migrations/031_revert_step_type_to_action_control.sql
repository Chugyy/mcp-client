-- Migration 031: Revert workflow_steps step_type to action/control
-- ============================================================================
-- Problème: La migration 028 a créé une incohérence entre:
--   - La contrainte DB qui accepte ('tool_call', 'llm_call', 'condition', 'loop')
--   - L'executor qui n'accepte que ('action', 'control')
--   - Les tests qui utilisent tous ('action', 'control')
--
-- Solution: Reverter vers l'architecture originale action/control qui est:
--   1. La source de vérité fonctionnelle (executor + 100% des tests)
--   2. Documentée dans AUTOMATION_ARCHITECTURE.md
--   3. Plus simple et extensible via step_subtype
-- ============================================================================

BEGIN;

-- 1. Supprimer l'ancienne contrainte
ALTER TABLE automation.workflow_steps
DROP CONSTRAINT IF EXISTS workflow_steps_step_type_check;

-- 2. Migrer les données existantes vers action/control
-- Règles de mapping (inverse de la migration 028):
--   'tool_call' → 'action' + step_subtype 'mcp_call'
--   'llm_call' → 'action' + step_subtype 'ai_action'
--   'condition' → 'control' + step_subtype 'condition'
--   'loop' → 'control' + step_subtype 'loop'

UPDATE automation.workflow_steps
SET
    step_type = CASE
        WHEN step_type = 'tool_call' THEN 'action'
        WHEN step_type = 'llm_call' THEN 'action'
        WHEN step_type = 'condition' THEN 'control'
        WHEN step_type = 'loop' THEN 'control'
        ELSE step_type  -- Si déjà action/control, garder tel quel
    END,
    step_subtype = CASE
        -- Pour tool_call: si pas de subtype ou subtype vide, utiliser 'mcp_call'
        WHEN step_type = 'tool_call' AND (step_subtype IS NULL OR step_subtype = '') THEN 'mcp_call'
        WHEN step_type = 'tool_call' THEN step_subtype  -- Garder le subtype existant

        -- Pour llm_call: si pas de subtype, utiliser 'ai_action'
        WHEN step_type = 'llm_call' AND (step_subtype IS NULL OR step_subtype = '') THEN 'ai_action'
        WHEN step_type = 'llm_call' THEN step_subtype  -- Garder le subtype existant

        -- Pour condition: si pas de subtype, utiliser 'condition'
        WHEN step_type = 'condition' AND (step_subtype IS NULL OR step_subtype = '') THEN 'condition'
        WHEN step_type = 'condition' THEN step_subtype  -- Garder le subtype existant

        -- Pour loop: si pas de subtype, utiliser 'loop'
        WHEN step_type = 'loop' AND (step_subtype IS NULL OR step_subtype = '') THEN 'loop'
        WHEN step_type = 'loop' THEN step_subtype  -- Garder le subtype existant

        -- Pour action/control déjà existants, garder tel quel
        ELSE step_subtype
    END;

-- 3. Ajouter la contrainte correcte (architecture originale)
ALTER TABLE automation.workflow_steps
ADD CONSTRAINT workflow_steps_step_type_check
CHECK (step_type IN ('action', 'control'));

-- 4. Mettre à jour les commentaires pour refléter l'architecture correcte
COMMENT ON COLUMN automation.workflow_steps.step_type IS
'Type principal du step (2 catégories):
- action: Exécute une action (MCP tool, agent IA, tool interne)
- control: Contrôle le flux d''exécution (condition, loop, delay)

Cette architecture simple permet d''ajouter de nouveaux step_subtype sans modifier la contrainte.';

COMMENT ON COLUMN automation.workflow_steps.step_subtype IS
'Sous-type spécifique pour les détails d''implémentation:

Pour step_type="action":
  - mcp_call: Appel d''un outil MCP externe
  - ai_action: Appel d''un agent IA (version simplifiée)
  - ai_agent: Appel d''un agent IA (version complète)
  - internal_tool: Appel d''un outil interne (search_resources, etc.)

Pour step_type="control":
  - condition: Branchement conditionnel (if/else, switch)
  - loop: Boucle (for_each, while, until)
  - delay: Pause temporelle

Cette liste peut être étendue sans modifier la base de données.';

-- 5. Vérification
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- Vérifier qu'aucun step n'a un step_type invalide
    SELECT COUNT(*) INTO invalid_count
    FROM automation.workflow_steps
    WHERE step_type NOT IN ('action', 'control');

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: % workflow steps still have invalid step_type', invalid_count;
    END IF;

    -- Vérifier que la contrainte existe
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_name = 'workflow_steps_step_type_check'
        AND constraint_schema = 'automation'
    ) THEN
        RAISE EXCEPTION 'Constraint workflow_steps_step_type_check was not created';
    END IF;

    RAISE NOTICE 'Migration 031 completed: workflow_steps.step_type reverted to action/control architecture';
END $$;

COMMIT;

-- ============================================================================
-- Architecture Finale (alignée avec executor et tests):
-- ============================================================================
-- step_type (2 catégories)            step_subtype (Détails implémentation)
-- ├─ action                           ├─ mcp_call
-- │                                   ├─ ai_action
-- │                                   ├─ ai_agent
-- │                                   └─ internal_tool
-- └─ control                          ├─ condition
--                                     ├─ loop
--                                     └─ delay
--
-- Exemples:
-- - action + mcp_call: Appel d'un outil MCP externe
-- - action + ai_action: Agent IA avec prompt simple
-- - control + condition: Branchement if/else
-- - control + loop: Boucle for_each
-- ============================================================================

-- ============================================================================
-- Rollback (si nécessaire):
-- ============================================================================
-- Cette migration peut être rollback avec la migration 028 si besoin
-- ============================================================================
