-- Ensure we're using the correct database
\c modporter;

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create vector extension with error handling
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE EXTENSION vector;
    END IF;
END $$;

-- Create document embeddings table for vector storage
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    embedding VECTOR(1536) NOT NULL,
    document_source VARCHAR NOT NULL,
    content_hash VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (id)
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Create conversion jobs table
CREATE TABLE IF NOT EXISTS conversion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    input_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create conversion results table
CREATE TABLE IF NOT EXISTS conversion_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    output_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create job progress table
CREATE TABLE IF NOT EXISTS job_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    progress INTEGER NOT NULL DEFAULT 0,
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create behavioral tests table
CREATE TABLE IF NOT EXISTS behavioral_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversion_id UUID REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    test_environment VARCHAR(100),
    minecraft_version VARCHAR(50),
    total_scenarios INTEGER DEFAULT 0,
    passed_scenarios INTEGER DEFAULT 0,
    failed_scenarios INTEGER DEFAULT 0,
    behavioral_score DECIMAL(3,2),
    test_config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create behavioral scenarios table
CREATE TABLE IF NOT EXISTS behavioral_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES behavioral_tests(id) ON DELETE CASCADE,
    scenario_name VARCHAR(255) NOT NULL,
    scenario_type VARCHAR(100),
    expected_behavior TEXT,
    actual_behavior TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    execution_time_ms INTEGER,
    state_changes JSONB,
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON conversion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON conversion_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_conversion_results_job_id ON conversion_results(job_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_tests_conversion_id ON behavioral_tests(conversion_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_scenarios_test_id ON behavioral_scenarios(test_id);
