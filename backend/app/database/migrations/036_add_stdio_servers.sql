-- Ajouter colonnes pour serveurs stdio (si elles n'existent pas)
ALTER TABLE servers
  ADD COLUMN IF NOT EXISTS args JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS env JSONB DEFAULT '{}';

-- Ajouter colonne type si elle n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'servers' AND column_name = 'type'
    ) THEN
        ALTER TABLE servers ADD COLUMN type TEXT DEFAULT 'http';
    END IF;
END $$;

-- Rendre url nullable (pas nécessaire pour stdio)
ALTER TABLE servers
  ALTER COLUMN url DROP NOT NULL;

-- Supprimer anciennes contraintes de type
ALTER TABLE servers
  DROP CONSTRAINT IF EXISTS servers_type_check;

ALTER TABLE servers
  DROP CONSTRAINT IF EXISTS check_stdio_has_command;

-- Ajouter nouvelle contrainte de type avec 4 valeurs
ALTER TABLE servers
  ADD CONSTRAINT servers_type_check
  CHECK (type IN ('http', 'npx', 'uvx', 'docker'));

-- Contrainte: url obligatoire si type='http'
ALTER TABLE servers
  DROP CONSTRAINT IF EXISTS check_http_has_url;

ALTER TABLE servers
  ADD CONSTRAINT check_http_has_url
  CHECK (type != 'http' OR url IS NOT NULL);

-- Index pour le type
CREATE INDEX IF NOT EXISTS idx_servers_type ON servers(type);

-- Statistiques
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 036 - MCP Simplified';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Types supportés: http, npx, uvx, docker';
    RAISE NOTICE 'Colonnes ajoutées: type, args, env';
    RAISE NOTICE '✅ Migration réussie';
END $$;
