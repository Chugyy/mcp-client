-- Migration 023 : Ajout du logo pour les services
-- Date: 2025-12-02
-- Description: Ajoute la colonne logo_upload_id à la table services pour stocker les logos des providers

-- ============================================================================
-- MODIFICATION : services (Ajout du champ logo)
-- ============================================================================

ALTER TABLE services ADD COLUMN IF NOT EXISTS logo_upload_id TEXT REFERENCES uploads(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_services_logo ON services(logo_upload_id);

-- ============================================================================
-- FIN DE LA MIGRATION 023
-- ============================================================================
