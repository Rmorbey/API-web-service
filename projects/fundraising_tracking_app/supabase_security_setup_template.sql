-- Supabase Security Setup Template
-- Replace [YOUR_PROJECT_URL] and [YOUR_SERVICE_KEY] with your actual values
-- This template creates a secure database schema for cache storage

-- Create a dedicated API schema
CREATE SCHEMA api;

-- Set search path for the API schema
ALTER ROLE postgres SET search_path TO api, public;
ALTER DATABASE "[YOUR_DATABASE_NAME]" SET search_path TO api, public;

-- Grant usage on the API schema to the service_role
GRANT USAGE ON SCHEMA api TO service_role;

-- Projects table (for multi-project support)
CREATE TABLE api.projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Cache storage table (project-aware)
CREATE TABLE api.cache_storage (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES api.projects(id),
    cache_type VARCHAR(50) NOT NULL, -- 'strava', 'fundraising', 'custom'
    data JSONB NOT NULL,
    last_fetch TIMESTAMP WITH TIME ZONE,
    last_rich_fetch TIMESTAMP WITH TIME ZONE,
    data_size INTEGER, -- Track data size for monitoring
    cache_version VARCHAR(20) DEFAULT '1.0', -- Version control for cache format
    retention_days INTEGER DEFAULT 30, -- Data retention policy
    metadata JSONB DEFAULT '{}', -- Flexible metadata storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, cache_type)
);

-- Indexes for performance
CREATE INDEX idx_api_cache_type ON api.cache_storage(cache_type);
CREATE INDEX idx_api_project_id ON api.cache_storage(project_id);
CREATE INDEX idx_api_updated_at ON api.cache_storage(updated_at);
CREATE INDEX idx_api_data_size ON api.cache_storage(data_size);

-- Row Level Security (RLS)
ALTER TABLE api.cache_storage ENABLE ROW LEVEL SECURITY;

-- Policy for service role full access (server-side only)
CREATE POLICY "Service role full access to cache_storage" ON api.cache_storage
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Deny all access to anon and authenticated roles for cache_storage
CREATE POLICY "Deny anon access to cache_storage" ON api.cache_storage
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "Deny authenticated access to cache_storage" ON api.cache_storage
    FOR ALL
    TO authenticated
    USING (false);

-- RLS for projects table
ALTER TABLE api.projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to projects" ON api.projects
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
CREATE POLICY "Deny anon access to projects" ON api.projects
    FOR ALL
    TO anon
    USING (false);
CREATE POLICY "Deny authenticated access to projects" ON api.projects
    FOR ALL
    TO authenticated
    USING (false);

-- Input Validation & Sanitization (PostgreSQL constraints)
ALTER TABLE api.cache_storage
ADD CONSTRAINT valid_cache_type
CHECK (cache_type IN ('strava', 'fundraising', 'custom'));

ALTER TABLE api.cache_storage
ADD CONSTRAINT valid_json_data
CHECK (jsonb_typeof(data) = 'object');

-- Add size limits to prevent DoS (10MB limit)
ALTER TABLE api.cache_storage
ADD CONSTRAINT data_size_limit
CHECK (octet_length(data::text) < 10485760);

-- Audit Logging
CREATE TABLE api.cache_audit_log (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES api.projects(id),
    cache_type VARCHAR(50) NOT NULL,
    operation VARCHAR(20) NOT NULL, -- 'READ', 'WRITE', 'UPDATE', 'DELETE'
    user_role VARCHAR(50), -- e.g., 'service_role'
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_size INTEGER,
    success BOOLEAN NOT NULL,
    details JSONB DEFAULT '{}'
);

-- RLS for audit log table (only service_role can read/write)
ALTER TABLE api.cache_audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to audit_log" ON api.cache_audit_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
CREATE POLICY "Deny anon access to audit_log" ON api.cache_audit_log
    FOR ALL
    TO anon
    USING (false);
CREATE POLICY "Deny authenticated access to audit_log" ON api.cache_audit_log
    FOR ALL
    TO authenticated
    USING (false);

-- Security Monitoring View (example)
CREATE VIEW api.security_analysis AS
SELECT
    ip_address,
    cache_type,
    operation,
    COUNT(*) as attempt_count,
    COUNT(CASE WHEN success = false THEN 1 END) as failed_count,
    MIN(timestamp) as first_attempt,
    MAX(timestamp) as last_attempt
FROM api.cache_audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY ip_address, cache_type, operation
HAVING COUNT(CASE WHEN success = false THEN 1 END) > 5;

-- Grant select on security_analysis view to service_role
GRANT SELECT ON api.security_analysis TO service_role;
