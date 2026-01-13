-- ============================================================================
-- Migration 041: Validations Optimization
-- ============================================================================
-- Date: 2025-12-10
-- Description: Ajout d'index pour optimiser les requêtes sur validations
--
-- Objectifs:
-- 1. Optimiser les filtres par user + status (GET /validations?status_filter=...)
-- 2. Optimiser les recherches par chat + status (cascade cancellation)
-- 3. Optimiser le tri par date de création
-- 4. Optimiser le cleanup des validations expirées (CRON job)
-- ============================================================================

BEGIN;

-- ============================================================================
-- INDEX DE PERFORMANCE
-- ============================================================================

-- 1. Index pour filtrage par user + status
-- Utilisé par: GET /validations?status_filter=pending
-- Améliore: list_validations_by_user(user_id, status)
CREATE INDEX IF NOT EXISTS idx_validations_user_status
ON validations(user_id, status);

COMMENT ON INDEX idx_validations_user_status IS
'Optimise GET /validations avec filtre status_filter. '
'Utilisé par ValidationManager.list_validations().';


-- 2. Index pour filtrage par chat + status
-- Utilisé par: cancel_all_pending_validations() lors du rejet
-- Améliore: Cascade cancellation après rejet d'une validation
CREATE INDEX IF NOT EXISTS idx_validations_chat_status
ON validations(chat_id, status)
WHERE status = 'pending';

COMMENT ON INDEX idx_validations_chat_status IS
'Optimise recherche validations pending par chat (cascade after rejection). '
'Partial index car seul "pending" est pertinent. '
'Utilisé par cancel_all_pending_validations().';


-- 3. Index pour tri par date de création
-- Utilisé par: GET /validations (tri par created_at DESC)
-- Améliore: list_validations_by_user() avec ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_validations_user_created
ON validations(user_id, created_at DESC);

COMMENT ON INDEX idx_validations_user_created IS
'Optimise tri par date de création (liste des validations). '
'Compound index (user_id, created_at) pour éviter sort après filtrage. '
'Utilisé par list_validations_by_user().';


-- 4. Index pour cleanup des validations expirées
-- Utilisé par: CRON job de nettoyage (expiration automatique)
-- Améliore: Recherche des validations expired mais pas encore marquées
CREATE INDEX IF NOT EXISTS idx_validations_expired
ON validations(expires_at)
WHERE status = 'pending' AND expires_at IS NOT NULL;

COMMENT ON INDEX idx_validations_expired IS
'Optimise nettoyage des validations expirées (CRON job). '
'Partial index car seul "pending" peut expirer. '
'WHERE expires_at IS NOT NULL évite NULL dans index. '
'Utilisé par cleanup_expired_validations() (future).';


-- 5. Index pour recherche par execution_id
-- Utilisé par: get_validations_by_execution() (debug/monitoring)
-- Améliore: Recherche de toutes les validations d'une execution donnée
CREATE INDEX IF NOT EXISTS idx_validations_execution
ON validations(execution_id)
WHERE execution_id IS NOT NULL;

COMMENT ON INDEX idx_validations_execution IS
'Optimise recherche par execution_id (debug/monitoring). '
'Partial index car execution_id est NULL pour validations manuelles. '
'Utilisé par get_validations_by_execution().';


-- ============================================================================
-- VÉRIFICATION DE PERFORMANCE
-- ============================================================================

-- Analyse de la table pour mettre à jour les statistiques PostgreSQL
ANALYZE validations;

-- ============================================================================
-- ROLLBACK (si nécessaire)
-- ============================================================================

-- Pour annuler cette migration:
-- DROP INDEX IF EXISTS idx_validations_user_status;
-- DROP INDEX IF EXISTS idx_validations_chat_status;
-- DROP INDEX IF EXISTS idx_validations_user_created;
-- DROP INDEX IF EXISTS idx_validations_expired;
-- DROP INDEX IF EXISTS idx_validations_execution;

COMMIT;

-- ============================================================================
-- FIN DE LA MIGRATION
-- ============================================================================
