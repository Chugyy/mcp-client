-- Migration: Ajouter updated_at et index pour validation_id
-- Date: 2025-01-05

-- Ajouter colonne updated_at
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Initialiser updated_at avec created_at pour les messages existants
UPDATE messages
SET updated_at = created_at
WHERE updated_at IS NULL;

-- Créer un index sur validation_id pour les lookups rapides
CREATE INDEX IF NOT EXISTS idx_messages_validation_id
ON messages ((metadata->>'validation_id'))
WHERE role = 'tool_call';

-- Trigger pour auto-update updated_at
CREATE OR REPLACE FUNCTION update_messages_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trigger_update_messages_updated_at ON messages;

CREATE TRIGGER trigger_update_messages_updated_at
BEFORE UPDATE ON messages
FOR EACH ROW
EXECUTE FUNCTION update_messages_updated_at();
