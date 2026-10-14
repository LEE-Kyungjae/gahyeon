CREATE TABLE stt_learning_rules (
    id VARCHAR(64) PRIMARY KEY,
    actor_id BIGINT NOT NULL,
    scope VARCHAR(80) NOT NULL,
    pipeline VARCHAR(64) NOT NULL,
    raw_text VARCHAR(512) NOT NULL,
    target_text VARCHAR(512),
    state VARCHAR(20) NOT NULL DEFAULT 'COLLECTING',
    validation_started TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_stt_rule_owner ON stt_learning_rules(actor_id, scope);
CREATE TABLE stt_learning_observations (
    id VARCHAR(64) PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL REFERENCES stt_learning_rules(id) ON DELETE CASCADE,
    raw_text VARCHAR(512) NOT NULL,
    effective_text VARCHAR(512) NOT NULL,
    expected_text VARCHAR(512),
    captured_at TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP
);
CREATE INDEX idx_stt_observation_rule ON stt_learning_observations(rule_id, captured_at);
