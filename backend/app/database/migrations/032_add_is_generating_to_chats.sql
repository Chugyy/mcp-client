-- Migration: Add is_generating column to chats table
-- Purpose: Lock concurrent message sending during LLM generation
-- Date: 2025-01-04

-- Add is_generating column to track if a chat is currently generating a response
ALTER TABLE chats
ADD COLUMN is_generating BOOLEAN DEFAULT FALSE NOT NULL;

-- Add index for faster lookups when checking generation status
CREATE INDEX idx_chats_is_generating ON chats(is_generating) WHERE is_generating = TRUE;

-- Add comment
COMMENT ON COLUMN chats.is_generating IS 'TRUE if chat is currently generating a response (prevents concurrent messages)';
