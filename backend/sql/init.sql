-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Alembic will manage table creation.
-- This file can be used for other non-Alembic managed DDL
-- or for seeding initial static data if necessary.