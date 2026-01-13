-- Migration 028: Fix workflow_steps step_type constraint
-- ============================================================================
-- Problème: La contrainte CHECK step_type IN ('action', 'control') n'est pas
--           cohérente avec l'API qui expose ('tool_call', 'llm_call', 'condition', 'loop')
-- Solution: Modifier la contrainte pour accepter les valeurs de l'API
--           et utiliser step_subtype pour les détails d'implémentation
-- ============================================================================

BEGIN;

-- 1. Supprimer l'ancienne contrainte
ALTER TABLE automation.workflow_steps
DROP CONSTRAINT IF EXISTS workflow_steps_step_type_check;

-- 2. Migrer les données existantes vers les nouvelles valeurs
-- Règles de mapping:
--   'action' + 'tool_call' → 'tool_call' + 'mcp_tool'
--   'action' + 'llm_call' → 'llm_call' + 'prompt'
--   'action' + (autre) → 'tool_call' + (step_subtype inchangé)
--   'control' + 'condition' → 'condition' + 'if_else'
--   'control' + 'loop' → 'loop' + 'for_each'
--   'control' + (autre) → 'condition' + (step_subtype inchangé)

-- Migrer les 'action' types
UPDATE automation.workflow_steps
SET step_type = CASE
    WHEN step_subtype = 'tool_call' OR step_subtype = 'mcp_tool' THEN 'tool_call'
    WHEN step_subtype = 'llm_call' OR step_subtype = 'prompt' THEN 'llm_call'
    ELSE 'tool_call'  -- Par défaut, les actions deviennent tool_call
END,
step_subtype = CASE
    WHEN step_subtype = 'tool_call' THEN 'mcp_tool'
    WHEN step_subtype = 'llm_call' THEN 'prompt'
    ELSE step_subtype  -- Garder le subtype existant
END
WHERE step_type = 'action';

-- Migrer les 'control' types
UPDATE automation.workflow_steps
SET step_type = CASE
    WHEN step_subtype IN ('loop', 'for_each', 'while') THEN 'loop'
    ELSE 'condition'  -- Par défaut, les contrôles deviennent condition
END,
step_subtype = CASE
    WHEN step_subtype = 'condition' THEN 'if_else'
    WHEN step_subtype = 'loop' THEN 'for_each'
    ELSE step_subtype  -- Garder le subtype existant
END
WHERE step_type = 'control';

-- 3. Ajouter la nouvelle contrainte avec les types de l'API
ALTER TABLE automation.workflow_steps
ADD CONSTRAINT workflow_steps_step_type_check
CHECK (step_type IN ('tool_call', 'llm_call', 'condition', 'loop'));

-- 4. Mettre à jour les commentaires pour refléter la nouvelle architecture
COMMENT ON COLUMN automation.workflow_steps.step_type IS
'Type principal du step (visible par l''utilisateur):
- tool_call: Appel d''un outil (MCP ou interne)
- llm_call: Appel d''un modèle LLM
- condition: Branchement conditionnel (if/else, switch)
- loop: Boucle (for_each, while)';

COMMENT ON COLUMN automation.workflow_steps.step_subtype IS
'Sous-type spécifique pour les détails d''implémentation.
Pour tool_call: mcp_tool, internal_tool, api_call
Pour llm_call: prompt, completion, chat
Pour condition: if_else, switch, ternary
Pour loop: for_each, while, until';

-- 5. Vérification
DO $$
BEGIN
    -- Vérifier que la contrainte a été mise à jour
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_name = 'workflow_steps_step_type_check'
        AND constraint_schema = 'automation'
    ) THEN
        RAISE EXCEPTION 'Constraint workflow_steps_step_type_check was not created';
    END IF;

    RAISE NOTICE 'Migration 028 completed: workflow_steps.step_type constraint updated successfully';
END $$;

COMMIT;

-- ============================================================================
-- Architecture Finale:
-- ============================================================================
-- step_type (Type principal)          step_subtype (Détails)
-- ├─ tool_call                        ├─ mcp_tool, internal_tool, api_call
-- ├─ llm_call                         ├─ prompt, completion, chat
-- ├─ condition                        ├─ if_else, switch, ternary
-- └─ loop                             └─ for_each, while, until
--
-- Exemples:
-- - tool_call + mcp_tool: Appel d'un outil MCP externe
-- - tool_call + internal_tool: Appel d'un outil interne (search_resources, etc.)
-- - llm_call + prompt: Génération de texte via prompt
-- - condition + if_else: Branchement if/else simple
-- - loop + for_each: Boucle sur un tableau
-- ============================================================================

-- ============================================================================
-- Rollback (si nécessaire):
-- ============================================================================
-- BEGIN;
-- ALTER TABLE automation.workflow_steps DROP CONSTRAINT workflow_steps_step_type_check;
-- ALTER TABLE automation.workflow_steps ADD CONSTRAINT workflow_steps_step_type_check
--   CHECK (step_type IN ('action', 'control'));
-- COMMIT;
-- ============================================================================
