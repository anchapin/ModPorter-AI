-- Migration: Add BYOK (Bring Your Own Key) fields to users table
-- Issue: #1227 - Security: BYOK API key vault

BEGIN;

-- Add BYOK-specific columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS llm_api_key_encrypted BYTEA,
ADD COLUMN IF NOT EXISTS llm_api_key_provider VARCHAR(20),
ADD COLUMN IF NOT EXISTS byok_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Drop the old string-based column if it exists (from issue #1226)
-- This handles migration from the old non-encrypted storage
ALTER TABLE users DROP COLUMN IF EXISTS llm_api_key_encrypted_string;

-- Add index for byok_enabled for faster BYOK user lookups
CREATE INDEX IF NOT EXISTS ix_users_byok_enabled ON users(byok_enabled) WHERE byok_enabled = TRUE;

-- Add index for provider lookup
CREATE INDEX IF NOT EXISTS ix_users_llm_api_key_provider ON users(llm_api_key_provider) WHERE llm_api_key_provider IS NOT NULL;

COMMIT;

-- Migration complete
-- To rollback:
-- BEGIN;
-- ALTER TABLE users DROP COLUMN IF EXISTS llm_api_key_encrypted;
-- ALTER TABLE users DROP COLUMN IF EXISTS llm_api_key_provider;
-- ALTER TABLE users DROP COLUMN IF EXISTS byok_enabled;
-- COMMIT;