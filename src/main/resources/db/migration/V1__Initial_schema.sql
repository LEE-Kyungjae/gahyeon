-- Initial schema for gahyeonbot
-- Based on BotConfig entity

CREATE TABLE bot_config (
    id BIGSERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value VARCHAR(500),
    description VARCHAR(200),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

-- Add index for faster lookups by config_key
CREATE INDEX idx_bot_config_key ON bot_config(config_key);

-- Add comment to table
COMMENT ON TABLE bot_config IS 'Bot configuration storage for dynamic settings and database connection testing';
COMMENT ON COLUMN bot_config.config_key IS 'Unique configuration key identifier';
COMMENT ON COLUMN bot_config.config_value IS 'Configuration value';
COMMENT ON COLUMN bot_config.description IS 'Description of the configuration';
COMMENT ON COLUMN bot_config.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN bot_config.updated_at IS 'Timestamp when the record was last updated';
