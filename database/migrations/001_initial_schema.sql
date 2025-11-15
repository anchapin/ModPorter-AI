-- Initial Production Schema Migration
-- This migration sets up the complete database schema for production

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Core tables for conversion management
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    input_file_path VARCHAR(512) NOT NULL,
    output_file_path VARCHAR(512),
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    conversion_type VARCHAR(100) NOT NULL, -- java_to_bedrock, bedrock_to_java, etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS conversion_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversion_id UUID REFERENCES conversions(id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI embedding dimension
    content_type VARCHAR(50) NOT NULL, -- code, metadata, etc.
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- QA results tables (from existing schema)
CREATE TABLE IF NOT EXISTS qa_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversion_id UUID REFERENCES conversions(id) ON DELETE CASCADE,
    test_suite_version VARCHAR(50) NOT NULL,
    total_tests INTEGER NOT NULL,
    passed_tests INTEGER NOT NULL,
    failed_tests INTEGER NOT NULL,
    warning_count INTEGER DEFAULT 0,
    performance_score DECIMAL(5,2),
    compatibility_score DECIMAL(5,2),
    overall_quality_score DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qa_test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qa_result_id UUID REFERENCES qa_results(id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    test_category VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    execution_time_ms INTEGER,
    error_message TEXT,
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- A/B testing tables
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    traffic_allocation INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_control BOOLEAN NOT NULL DEFAULT false,
    strategy_config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID REFERENCES experiment_variants(id) ON DELETE CASCADE,
    session_id UUID,
    kpi_quality DECIMAL(5,2),
    kpi_speed INTEGER,
    kpi_cost DECIMAL(10,2),
    user_feedback_score DECIMAL(3,2),
    user_feedback_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Production indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_conversions_project_id ON conversions(project_id);
CREATE INDEX IF NOT EXISTS idx_conversions_status ON conversions(status);
CREATE INDEX IF NOT EXISTS idx_conversions_created_at ON conversions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversions_type ON conversions(conversion_type);

CREATE INDEX IF NOT EXISTS idx_conversion_embeddings_conversion_id ON conversion_embeddings(conversion_id);
CREATE INDEX IF NOT EXISTS idx_conversion_embeddings_content_type ON conversion_embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_conversion_embeddings_vector ON conversion_embeddings USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_qa_results_conversion_id ON qa_results(conversion_id);
CREATE INDEX IF NOT EXISTS idx_qa_test_cases_qa_result_id ON qa_test_cases(qa_result_id);
CREATE INDEX IF NOT EXISTS idx_qa_test_cases_category ON qa_test_cases(test_category);
CREATE INDEX IF NOT EXISTS idx_qa_test_cases_status ON qa_test_cases(status);

CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiment_variants_experiment_id ON experiment_variants(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_results_variant_id ON experiment_results(variant_id);
CREATE INDEX IF NOT EXISTS idx_experiment_results_session_id ON experiment_results(session_id);

-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversions_updated_at BEFORE UPDATE ON conversions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_experiments_updated_at BEFORE UPDATE ON experiments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_experiment_variants_updated_at BEFORE UPDATE ON experiment_variants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) for multi-tenant security
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversions ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_test_cases ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own projects" ON projects FOR SELECT USING (owner_id = current_setting('app.current_user_id')::UUID);
CREATE POLICY "Users can insert their own projects" ON projects FOR INSERT WITH CHECK (owner_id = current_setting('app.current_user_id')::UUID);
CREATE POLICY "Users can update their own projects" ON projects FOR UPDATE USING (owner_id = current_setting('app.current_user_id')::UUID);
CREATE POLICY "Users can delete their own projects" ON projects FOR DELETE USING (owner_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY "Users can view conversions for their projects" ON conversions FOR SELECT USING (project_id IN (SELECT id FROM projects WHERE owner_id = current_setting('app.current_user_id')::UUID));
CREATE POLICY "Users can insert conversions for their projects" ON conversions FOR INSERT WITH CHECK (project_id IN (SELECT id FROM projects WHERE owner_id = current_setting('app.current_user_id')::UUID));
CREATE POLICY "Users can update conversions for their projects" ON conversions FOR UPDATE USING (project_id IN (SELECT id FROM projects WHERE owner_id = current_setting('app.current_user_id')::UUID));

-- Create a notification function for real-time updates
CREATE OR REPLACE FUNCTION notify_conversion_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('conversion_updates', 
        json_build_object(
            'type', TG_OP,
            'conversion_id', NEW.id,
            'status', COALESCE(NEW.status, OLD.status),
            'project_id', COALESCE(NEW.project_id, OLD.project_id)
        )::text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Add notification triggers
CREATE TRIGGER conversion_update_trigger
    AFTER INSERT OR UPDATE OR DELETE ON conversions
    FOR EACH ROW EXECUTE FUNCTION notify_conversion_update();
