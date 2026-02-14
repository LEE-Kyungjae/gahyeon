CREATE TABLE IF NOT EXISTS repo_readme_cache (
    id                 BIGSERIAL    PRIMARY KEY,
    repo_full_name     VARCHAR(255) NOT NULL,
    repo_url           VARCHAR(500) NOT NULL,
    readme_sha         VARCHAR(128) NOT NULL,
    readme_text        TEXT         NOT NULL,
    readme_fetched_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    summary_ko         TEXT,
    summary_ko_model   VARCHAR(100),
    summary_ko_updated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_repo_readme_cache_repo_sha
    ON repo_readme_cache(repo_full_name, readme_sha);

CREATE INDEX IF NOT EXISTS idx_repo_readme_cache_repo
    ON repo_readme_cache(repo_full_name);

CREATE INDEX IF NOT EXISTS idx_repo_readme_cache_fetched_at
    ON repo_readme_cache(readme_fetched_at);

CREATE INDEX IF NOT EXISTS idx_repo_readme_cache_summary_updated_at
    ON repo_readme_cache(summary_ko_updated_at);

