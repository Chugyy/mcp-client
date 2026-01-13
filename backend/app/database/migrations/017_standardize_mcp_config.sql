-- Migration 017: Standardiser les configs MCP sur "arguments"
-- Date: 2025-11-29
-- Objectif: Éliminer la confusion entre "params" et "arguments"
--           Garantir que tous les steps MCP ont une structure cohérente
--           Empêcher la création de configs invalides

-- Note: BEGIN/COMMIT géré automatiquement par le système de migration

-- ==============================================================================
-- ÉTAPE 1: Renommer "params" en "arguments" dans tous les steps MCP
-- ==============================================================================
-- Cible: Steps qui utilisent "params" mais n'ont pas "arguments"
-- Action: Copier "params" vers "arguments", puis supprimer "params"

UPDATE automation.workflow_steps
SET config = config - 'params' || jsonb_build_object('arguments', config->'params')
WHERE step_subtype = 'mcp_call'
  AND config ? 'params'
  AND NOT config ? 'arguments';

-- ==============================================================================
-- ÉTAPE 2: Nettoyer les steps avec "arguments" vide ET "params" présent
-- ==============================================================================
-- Cible: Steps qui ont à la fois "arguments": {} vide et "params" rempli
-- Action: Supprimer "arguments" vide pour que l'étape 1 puisse fonctionner

UPDATE automation.workflow_steps
SET config = config - 'arguments'
WHERE step_subtype = 'mcp_call'
  AND config ? 'arguments'
  AND config ? 'params'
  AND jsonb_typeof(config->'arguments') = 'object'
  AND (config->'arguments') = '{}'::jsonb;

-- Ré-exécuter l'étape 1 pour ces steps nettoyés
UPDATE automation.workflow_steps
SET config = config - 'params' || jsonb_build_object('arguments', config->'params')
WHERE step_subtype = 'mcp_call'
  AND config ? 'params'
  AND NOT config ? 'arguments';

-- ==============================================================================
-- ÉTAPE 3: Supprimer les steps MCP invalides (arguments vide sans params)
-- ==============================================================================
-- Cible: Steps invalides qui ne peuvent pas être réparés
-- Action: Suppression (ces steps sont inutilisables de toute façon)

DELETE FROM automation.workflow_steps
WHERE step_subtype = 'mcp_call'
  AND config ? 'arguments'
  AND jsonb_typeof(config->'arguments') = 'object'
  AND (config->'arguments') = '{}'::jsonb
  AND NOT config ? 'params';

-- ==============================================================================
-- ÉTAPE 4: Supprimer les steps MCP mal formés
-- ==============================================================================
-- Cible: Steps sans tool_name, server_id, ou arguments
-- Action: Suppression (ces steps sont invalides et non réparables)

DELETE FROM automation.workflow_steps
WHERE step_subtype = 'mcp_call'
  AND (
    NOT config ? 'tool_name' OR
    config->>'tool_name' = '' OR
    NOT config ? 'server_id' OR
    NOT config ? 'arguments'
  );

-- ==============================================================================
-- ÉTAPE 5: Supprimer complètement la clé "params" des configs restantes
-- ==============================================================================
-- Sécurité: Nettoyer toute trace de "params" dans les steps MCP

UPDATE automation.workflow_steps
SET config = config - 'params'
WHERE step_subtype = 'mcp_call'
  AND config ? 'params';

-- ==============================================================================
-- ÉTAPE 6: Ajouter contrainte CHECK pour empêcher configs invalides
-- ==============================================================================
-- IMPORTANT: Cette contrainte est ajoutée APRÈS le nettoyage
-- But: Garantir l'intégrité des données à long terme
-- Règles:
--   1. tool_name doit exister et être non vide
--   2. server_id doit exister
--   3. arguments doit exister et être un objet
--   4. arguments ne peut pas être vide

ALTER TABLE automation.workflow_steps
DROP CONSTRAINT IF EXISTS check_mcp_config;

ALTER TABLE automation.workflow_steps
ADD CONSTRAINT check_mcp_config
CHECK (
  step_subtype != 'mcp_call' OR (
    -- Pour les steps MCP uniquement:
    config ? 'tool_name' AND
    config->>'tool_name' != '' AND
    config ? 'server_id' AND
    config ? 'arguments' AND
    jsonb_typeof(config->'arguments') = 'object' AND
    config->'arguments' != '{}'::jsonb
  )
);

-- ==============================================================================
-- ÉTAPE 7: Créer des index pour améliorer les performances
-- ==============================================================================
-- But: Accélérer les requêtes par tool_name et server_id

-- Index pour recherche par tool_name
DROP INDEX IF EXISTS idx_workflow_steps_mcp_tool;
CREATE INDEX idx_workflow_steps_mcp_tool
ON automation.workflow_steps ((config->>'tool_name'))
WHERE step_subtype = 'mcp_call';

-- Index pour recherche par server_id
DROP INDEX IF EXISTS idx_workflow_steps_mcp_server;
CREATE INDEX idx_workflow_steps_mcp_server
ON automation.workflow_steps ((config->>'server_id'))
WHERE step_subtype = 'mcp_call';

-- ==============================================================================
-- ÉTAPE 8: Statistiques post-migration
-- ==============================================================================

DO $$
DECLARE
    total_mcp_steps INTEGER;
    steps_with_arguments INTEGER;
    steps_with_params INTEGER;
BEGIN
    -- Compter le total de steps MCP
    SELECT COUNT(*) INTO total_mcp_steps
    FROM automation.workflow_steps
    WHERE step_subtype = 'mcp_call';

    -- Compter les steps avec "arguments"
    SELECT COUNT(*) INTO steps_with_arguments
    FROM automation.workflow_steps
    WHERE step_subtype = 'mcp_call' AND config ? 'arguments';

    -- Compter les steps avec "params" (devrait être 0)
    SELECT COUNT(*) INTO steps_with_params
    FROM automation.workflow_steps
    WHERE step_subtype = 'mcp_call' AND config ? 'params';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 017 - Statistiques finales';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total steps MCP: %', total_mcp_steps;
    RAISE NOTICE 'Steps avec "arguments": %', steps_with_arguments;
    RAISE NOTICE 'Steps avec "params": % (doit être 0)', steps_with_params;

    IF steps_with_params > 0 THEN
        RAISE WARNING 'ATTENTION: % steps ont encore "params"!', steps_with_params;
    END IF;

    IF steps_with_arguments != total_mcp_steps THEN
        RAISE WARNING 'ATTENTION: % steps n''ont pas "arguments"!', (total_mcp_steps - steps_with_arguments);
    END IF;

    IF steps_with_arguments = total_mcp_steps AND steps_with_params = 0 THEN
        RAISE NOTICE '✅ Migration réussie: tous les steps MCP utilisent "arguments"';
    END IF;
END $$;
