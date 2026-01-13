-- ============================================================================
-- Migration 013.5: Move generate_prefixed_id function to core schema
-- ============================================================================
-- Description: Move generate_prefixed_id from public to core schema
--              This should be run after migration 013 (create_schemas)
--              and before any migration that references core.generate_prefixed_id
-- ============================================================================

-- Move function from public to core if it exists in public
DO $$
BEGIN
    -- Check if function exists in public schema
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'generate_prefixed_id'
    ) THEN
        -- Move function to core schema
        ALTER FUNCTION public.generate_prefixed_id(TEXT) SET SCHEMA core;
        RAISE NOTICE 'Function generate_prefixed_id moved from public to core schema';
    ELSIF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'core'
        AND p.proname = 'generate_prefixed_id'
    ) THEN
        -- Function already in core schema
        RAISE NOTICE 'Function generate_prefixed_id already in core schema';
    ELSE
        -- Function doesn't exist, create it in core schema
        CREATE OR REPLACE FUNCTION core.generate_prefixed_id(prefix TEXT)
        RETURNS TEXT AS $func$
        DECLARE
          chars TEXT := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
          result TEXT := '';
          i INTEGER;
        BEGIN
          FOR i IN 1..6 LOOP
            result := result || substr(chars, floor(random() * length(chars) + 1)::int, 1);
          END LOOP;
          RETURN prefix || '_' || result;
        END;
        $func$ LANGUAGE plpgsql;

        RAISE NOTICE 'Function generate_prefixed_id created in core schema';
    END IF;
END $$;

-- Verification
DO $$
BEGIN
    -- Verify function exists in core schema
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'core'
        AND p.proname = 'generate_prefixed_id'
    ) THEN
        RAISE EXCEPTION 'Function core.generate_prefixed_id does not exist';
    END IF;

    -- Test the function
    PERFORM core.generate_prefixed_id('test');

    RAISE NOTICE '✅ Migration 013.5 completed: generate_prefixed_id is in core schema and working';
END $$;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. This migration is idempotent and can be run multiple times safely
-- 2. After this migration, all DEFAULT clauses should use core.generate_prefixed_id
-- 3. The function in public schema (if it existed) is moved to core
-- ============================================================================
