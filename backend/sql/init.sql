-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS conversion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    input_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversion_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    output_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    progress INTEGER NOT NULL DEFAULT 0,
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE behavioral_tests (
    id UUID PRIMARY KEY,
    conversion_id UUID REFERENCES conversions(id),
    test_environment VARCHAR(100),
    minecraft_version VARCHAR(50),
    total_scenarios INTEGER,
    passed_scenarios INTEGER,
    failed_scenarios INTEGER,
    behavioral_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE behavioral_scenarios (
    id UUID PRIMARY KEY,
    test_id UUID REFERENCES behavioral_tests(id),
    scenario_name VARCHAR(255),
    scenario_type VARCHAR(100),
    expected_behavior TEXT,
    actual_behavior TEXT,
    status VARCHAR(20),
    execution_time_ms INTEGER,
    state_changes JSONB
);