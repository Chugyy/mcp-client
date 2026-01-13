-- Migration 043: Make auth_type nullable for stdio servers (npx, uvx, docker)
-- Since stdio servers don't use HTTP authentication, auth_type should be NULL for them

-- Drop the NOT NULL constraint on auth_type
ALTER TABLE mcp.servers ALTER COLUMN auth_type DROP NOT NULL;

-- Add a CHECK constraint: if type='http', auth_type must be specified
ALTER TABLE mcp.servers ADD CONSTRAINT servers_http_requires_auth_type
    CHECK (type != 'http' OR auth_type IS NOT NULL);

-- Verify
DO $$
BEGIN
    RAISE NOTICE 'Migration 043: auth_type is now nullable for stdio servers';
    RAISE NOTICE 'HTTP servers still require auth_type via CHECK constraint';
END $$;
