-- ============================================================================
-- Migration 012: RAG System
-- ============================================================================
-- Description: Ajoute le système RAG complet pour les ressources
--   - Lie uploads aux ressources
--   - Simplifie resources (supprime colonnes cloud API)
--   - Ajoute pgvector pour recherche sémantique
--   - Table embeddings pour stocker chunks + vecteurs

-- 1. Ajouter resource_id dans uploads (relation 1-N) - IDEMPOTENT
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'uploads' AND column_name = 'resource_id'
  ) THEN
    ALTER TABLE uploads ADD COLUMN resource_id TEXT REFERENCES resources(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_uploads_resource_id ON uploads(resource_id);

-- 2. Ajouter type 'resource' dans uploads - IDEMPOTENT
DO $$
BEGIN
  ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_type_check;
  ALTER TABLE uploads ADD CONSTRAINT uploads_type_check
    CHECK (type IN ('avatar', 'document', 'resource'));
END $$;

-- 3. Simplifier resources (supprimer colonnes cloud API non utilisées)
ALTER TABLE resources DROP COLUMN IF EXISTS type;
ALTER TABLE resources DROP COLUMN IF EXISTS config;
ALTER TABLE resources DROP COLUMN IF EXISTS methods;
ALTER TABLE resources DROP COLUMN IF EXISTS service_id;

-- 4. Ajouter colonnes RAG dans resources - IDEMPOTENT
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'status') THEN
    ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'error'));
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'chunk_count') THEN
    ALTER TABLE resources ADD COLUMN chunk_count INTEGER DEFAULT 0;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'embedding_model') THEN
    ALTER TABLE resources ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-3-large';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'embedding_dim') THEN
    ALTER TABLE resources ADD COLUMN embedding_dim INTEGER DEFAULT 3072;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'indexed_at') THEN
    ALTER TABLE resources ADD COLUMN indexed_at TIMESTAMPTZ;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'resources' AND column_name = 'error_message') THEN
    ALTER TABLE resources ADD COLUMN error_message TEXT;
  END IF;
END $$;

-- 5. Activer pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 6. Table embeddings (dimension fixe, configurable via settings) - IDEMPOTENT
CREATE TABLE IF NOT EXISTS embeddings (
  id TEXT PRIMARY KEY DEFAULT generate_prefixed_id('emb'),
  resource_id TEXT NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  vector halfvec(3072),  -- halfvec supporte jusqu'à 4000 dimensions (vs 2000 pour vector)
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_resource_id ON embeddings(resource_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_upload_id ON embeddings(upload_id);
-- Utiliser halfvec + HNSW pour supporter 3072 dimensions (limite vector = 2000)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING hnsw (vector halfvec_cosine_ops);

-- ============================================================================
-- Migration Complete
-- ============================================================================
