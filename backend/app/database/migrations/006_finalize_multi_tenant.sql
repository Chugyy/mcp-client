-- Migration 006 : Finalisation de l'architecture multi-tenant
-- Date: 2025-11-26
-- Description: Rendre user_id et service_id obligatoires, supprimer colonnes obsolètes

-- ============================================================================
-- ÉTAPE 1 : Rendre user_id obligatoire dans api_keys
-- ============================================================================

-- Note: Avant d'exécuter cette migration, s'assurer qu'il n'y a pas de clés orphelines
-- SELECT COUNT(*) FROM api_keys WHERE user_id IS NULL;
-- Si des clés existent sans user_id, les migrer ou les supprimer manuellement

ALTER TABLE api_keys ALTER COLUMN user_id SET NOT NULL;

-- ============================================================================
-- ÉTAPE 2 : Rendre service_id obligatoire dans api_keys
-- ============================================================================

-- Note: Avant d'exécuter, s'assurer qu'il n'y a pas de clés sans service_id
-- SELECT COUNT(*) FROM api_keys WHERE service_id IS NULL;

ALTER TABLE api_keys ALTER COLUMN service_id SET NOT NULL;

-- ============================================================================
-- ÉTAPE 3 : Supprimer les colonnes obsolètes dans servers
-- ============================================================================

-- Supprimer la colonne api_key (plaintext - risque de sécurité)
ALTER TABLE servers DROP COLUMN IF EXISTS api_key;

-- Supprimer api_key_id (remplacé par service_id)
ALTER TABLE servers DROP COLUMN IF EXISTS api_key_id;

-- ============================================================================
-- ÉTAPE 4 : Supprimer les colonnes obsolètes dans resources
-- ============================================================================

-- Supprimer api_key_id (remplacé par service_id)
ALTER TABLE resources DROP COLUMN IF EXISTS api_key_id;

-- ============================================================================
-- VÉRIFICATIONS POST-MIGRATION
-- ============================================================================

-- Vérifier que user_id est NOT NULL
-- SELECT column_name, is_nullable FROM information_schema.columns
-- WHERE table_name = 'api_keys' AND column_name = 'user_id';
-- Résultat attendu: is_nullable = 'NO'

-- Vérifier que service_id est NOT NULL
-- SELECT column_name, is_nullable FROM information_schema.columns
-- WHERE table_name = 'api_keys' AND column_name = 'service_id';
-- Résultat attendu: is_nullable = 'NO'

-- Vérifier que les colonnes obsolètes n'existent plus
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'servers' AND column_name IN ('api_key', 'api_key_id');
-- Résultat attendu: 0 lignes

-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'resources' AND column_name = 'api_key_id';
-- Résultat attendu: 0 lignes

-- ============================================================================
-- FIN DE LA MIGRATION 006
-- ============================================================================
