-- Migration 024 : Ajout du support pour les logos de services dans la table uploads
-- Date: 2025-12-02
-- Description: Ajoute la colonne service_id et le type 'service_logo' pour stocker les logos des providers

-- ============================================================================
-- MODIFICATION : uploads (Ajout de service_id et type service_logo)
-- ============================================================================

-- Ajouter la colonne service_id
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS service_id TEXT REFERENCES services(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_uploads_service_id ON uploads(service_id);

-- Supprimer l'ancienne contrainte CHECK sur le type
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_type_check;

-- Ajouter 'service_logo' aux types possibles (en gardant 'resource')
ALTER TABLE uploads ADD CONSTRAINT uploads_type_check CHECK (
  type IN ('avatar', 'document', 'resource', 'service_logo')
);

-- Supprimer l'ancienne contrainte qui n'autorisait que user_id, agent_id, resource_id
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_check;

-- Nouvelle contrainte qui autorise exactement UN des quatre champs
ALTER TABLE uploads ADD CONSTRAINT uploads_check CHECK (
  (
    (user_id IS NOT NULL)::int +
    (agent_id IS NOT NULL)::int +
    (resource_id IS NOT NULL)::int +
    (service_id IS NOT NULL)::int
  ) = 1
);

-- ============================================================================
-- FIN DE LA MIGRATION 024
-- ============================================================================
