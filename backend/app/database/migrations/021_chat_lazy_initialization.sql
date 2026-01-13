-- Migration: Chat Lazy Initialization
-- Description: Enable lazy initialization of chats by allowing empty chats without agent/team
-- Date: 2025-12-01

-- Step 1: Drop existing constraint that blocks empty chats
ALTER TABLE chats DROP CONSTRAINT IF EXISTS chats_check;

-- Step 2: Add new columns for lazy initialization
ALTER TABLE chats ADD COLUMN model TEXT;
ALTER TABLE chats ADD COLUMN initialized_at TIMESTAMPTZ;

-- Step 3: Update existing chats to mark them as initialized
UPDATE chats
SET initialized_at = created_at,
    model = 'gpt-4o-mini'
WHERE initialized_at IS NULL;

-- Step 4: Add new constraint allowing empty OR initialized chats
ALTER TABLE chats ADD CONSTRAINT chats_initialization_check CHECK (
    -- Allow empty uninitialized chats
    (initialized_at IS NULL AND agent_id IS NULL AND team_id IS NULL AND model IS NULL)
    OR
    -- Allow initialized chats with agent
    (initialized_at IS NOT NULL AND agent_id IS NOT NULL AND team_id IS NULL AND model IS NOT NULL)
    OR
    -- Allow initialized chats with team
    (initialized_at IS NOT NULL AND agent_id IS NULL AND team_id IS NOT NULL AND model IS NOT NULL)
);

-- Step 5: Create index for uninitialized chats
CREATE INDEX idx_chats_uninitialized ON chats(initialized_at, created_at)
WHERE initialized_at IS NULL;

-- Step 6: Create index for model column
CREATE INDEX idx_chats_model ON chats(model);

-- Step 7: Add comments for documentation
COMMENT ON COLUMN chats.model IS 'AI model used for this chat (e.g., gpt-4o-mini). NULL for uninitialized chats.';
COMMENT ON COLUMN chats.initialized_at IS 'Timestamp when chat was initialized with first message. NULL for empty chats awaiting initialization.';
COMMENT ON CONSTRAINT chats_initialization_check ON chats IS 'Ensures chats are either uninitialized (all NULL) or properly initialized with agent/team and model.';
