-- Table to store overall results for a QA run against a specific conversion
CREATE TABLE qa_results (
    id UUID PRIMARY KEY,
    conversion_id UUID REFERENCES conversions(id) ON DELETE CASCADE, -- Assuming a 'conversions' table exists
    test_suite_version VARCHAR(50) NOT NULL, -- Version of the test suite used
    total_tests INTEGER NOT NULL,
    passed_tests INTEGER NOT NULL,
    failed_tests INTEGER NOT NULL,
    warning_count INTEGER DEFAULT 0,
    performance_score DECIMAL(5,2), -- Overall performance score (e.g., 0.00 to 100.00 or 0.00 to 1.00)
    compatibility_score DECIMAL(5,2), -- Overall compatibility score
    overall_quality_score DECIMAL(5,2), -- Overall quality score based on QA
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to store results for individual test cases within a QA run
CREATE TABLE qa_test_cases (
    id UUID PRIMARY KEY,
    qa_result_id UUID REFERENCES qa_results(id) ON DELETE CASCADE, -- Links to the parent QA run
    test_name VARCHAR(255) NOT NULL,
    test_category VARCHAR(100) NOT NULL, -- e.g., functional, performance, compatibility, integration, stress, regression
    status VARCHAR(20) NOT NULL, -- e.g., passed, failed, skipped, warning
    execution_time_ms INTEGER, -- Execution time in milliseconds
    error_message TEXT, -- Detailed error message if the test failed
    performance_metrics JSONB, -- For storing various performance data (e.g., CPU, memory, FPS)
    -- Could also include:
    -- logs_summary TEXT, -- Summary of relevant logs or link to full logs
    -- screenshot_path VARCHAR(512), -- Path to a screenshot on failure (if applicable)
    -- video_path VARCHAR(512) -- Path to a video recording (if applicable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to store A/B testing experiments
CREATE TABLE experiments (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, active, paused, completed
    traffic_allocation INTEGER NOT NULL DEFAULT 100, -- Percentage of traffic to allocate to experiment (0-100)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to store variants within an experiment
CREATE TABLE experiment_variants (
    id UUID PRIMARY KEY,
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- Name of the variant (e.g., 'control', 'new_strategy_v1')
    description TEXT,
    is_control BOOLEAN NOT NULL DEFAULT false, -- Whether this is the control group
    strategy_config JSONB, -- Configuration for the agent strategy
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to store results from A/B testing experiments
CREATE TABLE experiment_results (
    id UUID PRIMARY KEY,
    variant_id UUID REFERENCES experiment_variants(id) ON DELETE CASCADE,
    session_id UUID, -- Links to the conversion session
    kpi_quality DECIMAL(5,2), -- Quality score (0.00 to 100.00)
    kpi_speed INTEGER, -- Execution time in milliseconds
    kpi_cost DECIMAL(10,2), -- Computational cost (e.g., token usage)
    user_feedback_score DECIMAL(3,2), -- User feedback score (e.g., 1.0 to 5.0)
    user_feedback_text TEXT, -- Optional text feedback from user
    metadata JSONB, -- Additional metadata about the conversion
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add indexes for frequently queried columns
CREATE INDEX idx_qa_results_conversion_id ON qa_results(conversion_id);
CREATE INDEX idx_qa_test_cases_qa_result_id ON qa_test_cases(qa_result_id);
CREATE INDEX idx_qa_test_cases_category ON qa_test_cases(test_category);
CREATE INDEX idx_qa_test_cases_status ON qa_test_cases(status);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiment_variants_experiment_id ON experiment_variants(experiment_id);
CREATE INDEX idx_experiment_results_variant_id ON experiment_results(variant_id);
CREATE INDEX idx_experiment_results_session_id ON experiment_results(session_id);

-- Comments on schema:
-- - UUIDs are used for primary keys for global uniqueness.
-- - 'conversions(id)' is assumed to be an existing table from other parts of the project.
--   If it doesn't exist, the FOREIGN KEY constraint might need to be adjusted or removed initially.
-- - DECIMAL(5,2) for scores assumes a range like 0.00 to 100.00 or similar precision.
-- - JSONB for performance_metrics allows flexible storage of various metrics.
-- - `WITH TIME ZONE` for timestamps is generally good practice.
-- - Added `ON DELETE CASCADE` for foreign keys so test cases are removed if the parent result is removed.
-- - Added tables for A/B testing infrastructure with proper relationships and indexes.
