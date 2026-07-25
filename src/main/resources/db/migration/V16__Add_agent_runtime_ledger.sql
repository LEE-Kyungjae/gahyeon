CREATE TABLE agent_sessions (
    id VARCHAR(36) PRIMARY KEY,
    session_key VARCHAR(200) NOT NULL UNIQUE,
    gateway VARCHAR(20) NOT NULL,
    guild_id BIGINT,
    user_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_agent_sessions_user_updated
    ON agent_sessions(user_id, updated_at DESC);

CREATE TABLE agent_runs (
    id VARCHAR(36) PRIMARY KEY,
    request_id VARCHAR(120) NOT NULL UNIQUE,
    session_id VARCHAR(36) NOT NULL REFERENCES agent_sessions(id),
    gateway VARCHAR(20) NOT NULL,
    guild_id BIGINT,
    user_id BIGINT NOT NULL,
    username VARCHAR(100) NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT,
    status VARCHAR(30) NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 0,
    max_steps INTEGER NOT NULL,
    next_event_sequence BIGINT NOT NULL DEFAULT 1,
    error_code VARCHAR(100),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_agent_runs_session_created
    ON agent_runs(session_id, created_at DESC);
CREATE INDEX idx_agent_runs_status_updated
    ON agent_runs(status, updated_at);

CREATE TABLE agent_run_events (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    sequence BIGINT NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    step INTEGER NOT NULL DEFAULT 0,
    tool_name VARCHAR(120),
    payload TEXT,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_agent_run_event_sequence UNIQUE(run_id, sequence)
);

CREATE INDEX idx_agent_run_events_run_sequence
    ON agent_run_events(run_id, sequence);
