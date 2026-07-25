CREATE TABLE agent_background_jobs (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    job_type VARCHAR(100) NOT NULL,
    payload TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    available_at TIMESTAMP NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    locked_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_agent_background_jobs_due
    ON agent_background_jobs(status, available_at);
