-- PACTS v3.0 Database Schema
-- Memory & Persistence Layer

-- =============================================================================
-- Table: runs
-- Purpose: Store test run metadata
-- =============================================================================
CREATE TABLE IF NOT EXISTS runs (
    req_id VARCHAR(50) PRIMARY KEY,
    test_name VARCHAR(200),
    url TEXT,
    status VARCHAR(20) NOT NULL,  -- 'pass', 'fail', 'error'
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    heal_rounds INTEGER DEFAULT 0,
    heal_events INTEGER DEFAULT 0,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_start_time ON runs(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_runs_test_name ON runs(test_name);

-- =============================================================================
-- Table: run_steps
-- Purpose: Store step-level execution details
-- =============================================================================
CREATE TABLE IF NOT EXISTS run_steps (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(50) REFERENCES runs(req_id) ON DELETE CASCADE,
    step_idx INTEGER NOT NULL,
    element VARCHAR(200),
    action VARCHAR(50),
    value TEXT,
    selector TEXT,
    strategy VARCHAR(50),
    confidence DECIMAL(3,2),
    outcome VARCHAR(20),  -- 'success', 'healed', 'failed'
    heal_attempts INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    error_message TEXT,
    screenshot_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (req_id, step_idx)
);

CREATE INDEX IF NOT EXISTS idx_run_steps_req_id ON run_steps(req_id);
CREATE INDEX IF NOT EXISTS idx_run_steps_element ON run_steps(element);
CREATE INDEX IF NOT EXISTS idx_run_steps_outcome ON run_steps(outcome);

-- =============================================================================
-- Table: artifacts
-- Purpose: Store screenshots, HTML snapshots, DOM hashes
-- =============================================================================
CREATE TABLE IF NOT EXISTS artifacts (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(50) REFERENCES runs(req_id) ON DELETE CASCADE,
    step_idx INTEGER,
    artifact_type VARCHAR(20),  -- 'screenshot', 'html', 'dom_hash'
    file_path TEXT,
    file_size INTEGER,
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_req_id ON artifacts(req_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);

-- =============================================================================
-- Table: selector_cache
-- Purpose: Persistent POM cache for selector memory
-- =============================================================================
CREATE TABLE IF NOT EXISTS selector_cache (
    id SERIAL PRIMARY KEY,
    url_pattern TEXT NOT NULL,     -- e.g., "https://saucedemo.com/%"
    element_name VARCHAR(200) NOT NULL,
    selector TEXT NOT NULL,
    strategy VARCHAR(50),
    confidence DECIMAL(3,2),
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    last_verified_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (url_pattern, element_name)
);

CREATE INDEX IF NOT EXISTS idx_selector_cache_url ON selector_cache(url_pattern);
CREATE INDEX IF NOT EXISTS idx_selector_cache_element ON selector_cache(element_name);
CREATE INDEX IF NOT EXISTS idx_selector_cache_last_verified ON selector_cache(last_verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_selector_cache_hit_count ON selector_cache(hit_count DESC);

-- =============================================================================
-- Table: heal_history
-- Purpose: Track healing strategy success rates
-- =============================================================================
CREATE TABLE IF NOT EXISTS heal_history (
    id SERIAL PRIMARY KEY,
    element_name VARCHAR(200),
    url_pattern TEXT,
    strategy VARCHAR(50),
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_heal_time_ms INTEGER,
    last_used_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (element_name, url_pattern, strategy)
);

CREATE INDEX IF NOT EXISTS idx_heal_history_element ON heal_history(element_name);
CREATE INDEX IF NOT EXISTS idx_heal_history_success_rate ON heal_history((success_count::float / NULLIF(success_count + failure_count, 0)) DESC);

-- =============================================================================
-- Table: metrics
-- Purpose: Store aggregated metrics for analytics
-- =============================================================================
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    req_id VARCHAR(50) REFERENCES runs(req_id) ON DELETE CASCADE,
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,2),
    metric_unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_req_id ON metrics(req_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);

-- =============================================================================
-- Views: Useful analytics views
-- =============================================================================

-- View: run_summary
-- Purpose: Quick overview of test runs
CREATE OR REPLACE VIEW run_summary AS
SELECT
    req_id,
    test_name,
    status,
    completed_steps || '/' || total_steps AS steps,
    heal_rounds,
    duration_ms,
    start_time
FROM runs
ORDER BY start_time DESC
LIMIT 100;

-- View: selector_cache_stats
-- Purpose: Cache hit rate analysis
CREATE OR REPLACE VIEW selector_cache_stats AS
SELECT
    element_name,
    url_pattern,
    selector,
    strategy,
    hit_count,
    miss_count,
    ROUND(hit_count::numeric / NULLIF(hit_count + miss_count, 0) * 100, 2) AS hit_rate_pct,
    last_verified_at
FROM selector_cache
ORDER BY hit_count DESC;

-- View: healing_success_rate
-- Purpose: Best healing strategies
CREATE OR REPLACE VIEW healing_success_rate AS
SELECT
    element_name,
    url_pattern,
    strategy,
    success_count,
    failure_count,
    ROUND(success_count::numeric / NULLIF(success_count + failure_count, 0) * 100, 2) AS success_rate_pct,
    avg_heal_time_ms,
    last_used_at
FROM heal_history
ORDER BY success_rate_pct DESC, success_count DESC;

-- =============================================================================
-- Functions: Helper functions for analytics
-- =============================================================================

-- Function: get_daily_success_rate
-- Purpose: Calculate daily success rate for trend analysis
CREATE OR REPLACE FUNCTION get_daily_success_rate(days INTEGER DEFAULT 30)
RETURNS TABLE (
    date DATE,
    total_runs BIGINT,
    passed_runs BIGINT,
    success_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(start_time) AS date,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'pass') AS passed_runs,
        ROUND(
            COUNT(*) FILTER (WHERE status = 'pass')::numeric /
            NULLIF(COUNT(*), 0) * 100,
            2
        ) AS success_rate
    FROM runs
    WHERE start_time >= NOW() - INTERVAL '1 day' * days
    GROUP BY DATE(start_time)
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: cleanup_old_runs
-- Purpose: Delete runs older than specified days (default 30)
CREATE OR REPLACE FUNCTION cleanup_old_runs(days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM runs
    WHERE created_at < NOW() - INTERVAL '1 day' * days;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Initial Data: Sample configuration
-- =============================================================================

-- Create SYSTEM run for configuration metrics
INSERT INTO runs (req_id, test_name, url, status, total_steps, completed_steps, start_time)
VALUES ('SYSTEM', 'System Configuration', 'N/A', 'pass', 0, 0, NOW())
ON CONFLICT (req_id) DO NOTHING;

-- Insert sample metrics configuration
INSERT INTO metrics (req_id, metric_name, metric_value, metric_unit)
VALUES ('SYSTEM', 'cache_ttl_seconds', 3600, 'seconds')
ON CONFLICT DO NOTHING;

INSERT INTO metrics (req_id, metric_name, metric_value, metric_unit)
VALUES ('SYSTEM', 'max_heal_rounds', 3, 'count')
ON CONFLICT DO NOTHING;

INSERT INTO metrics (req_id, metric_name, metric_value, metric_unit)
VALUES ('SYSTEM', 'selector_cache_retention_days', 7, 'days')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Grants: Permissions for application user
-- =============================================================================

-- Grant all privileges to pacts user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pacts;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pacts;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO pacts;

-- =============================================================================
-- Schema Version Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(10) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('3.0.0', 'Initial v3.0 schema with memory and persistence')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- End of Schema
-- =============================================================================
