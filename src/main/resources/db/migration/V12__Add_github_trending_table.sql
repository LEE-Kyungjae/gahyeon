CREATE TABLE github_trending (
    id             BIGSERIAL    PRIMARY KEY,
    snapshot_date  DATE         NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    repo_url       VARCHAR(500) NOT NULL,
    description    TEXT,
    language       VARCHAR(100),
    stars_total    INTEGER      NOT NULL DEFAULT 0,
    stars_period   INTEGER,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_github_trending_snapshot_date ON github_trending(snapshot_date);
CREATE UNIQUE INDEX idx_github_trending_date_repo ON github_trending(snapshot_date, repo_full_name);
