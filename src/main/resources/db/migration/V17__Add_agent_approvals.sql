CREATE TABLE agent_approvals (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    tool_name VARCHAR(120) NOT NULL,
    tool_arguments TEXT NOT NULL,
    argument_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    decided_at TIMESTAMP,
    decided_by BIGINT,
    consumed_at TIMESTAMP,
    CONSTRAINT uq_agent_approval_call UNIQUE(run_id, tool_name, argument_hash)
);

CREATE INDEX idx_agent_approvals_run_status
    ON agent_approvals(run_id, status);
