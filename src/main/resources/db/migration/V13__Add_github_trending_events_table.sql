CREATE TABLE IF NOT EXISTS github_trending_events (
    id             BIGSERIAL    PRIMARY KEY,
    snapshot_date  DATE         NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    repo_url       VARCHAR(500) NOT NULL,
    description    TEXT,
    language       VARCHAR(100),
    stars_total    INTEGER      NOT NULL DEFAULT 0,
    stars_period   INTEGER,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_github_trending_events_snapshot_date
    ON github_trending_events(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_github_trending_events_sent_at
    ON github_trending_events(sent_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_github_trending_events_date_repo
    ON github_trending_events(snapshot_date, repo_full_name);

