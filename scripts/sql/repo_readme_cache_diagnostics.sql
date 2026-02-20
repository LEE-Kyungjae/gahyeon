-- repo_readme_cache diagnostics and optional remediation
-- target table: repo_readme_cache
-- safe to run read-only sections repeatedly

-- ============================================================
-- 1) overview
-- ============================================================
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT repo_full_name) AS total_repos,
  COUNT(*) FILTER (WHERE summary_ko IS NULL OR BTRIM(summary_ko) = '') AS rows_missing_summary,
  COUNT(*) FILTER (WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> '') AS rows_with_summary
FROM repo_readme_cache;

-- latest row per repo by (readme_fetched_at desc, id desc)
WITH latest AS (
  SELECT DISTINCT ON (repo_full_name)
         id, repo_full_name, readme_sha, readme_fetched_at, summary_ko, summary_ko_updated_at
  FROM repo_readme_cache
  ORDER BY repo_full_name, readme_fetched_at DESC, id DESC
)
SELECT
  COUNT(*) AS latest_rows,
  COUNT(*) FILTER (WHERE summary_ko IS NULL OR BTRIM(summary_ko) = '') AS latest_missing_summary,
  COUNT(*) FILTER (WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> '') AS latest_with_summary
FROM latest;

-- ============================================================
-- 2) fallback candidates
-- latest has no summary, but older row has summary (same repo)
-- ============================================================
WITH latest AS (
  SELECT DISTINCT ON (repo_full_name)
         id, repo_full_name, readme_sha, readme_fetched_at, summary_ko
  FROM repo_readme_cache
  ORDER BY repo_full_name, readme_fetched_at DESC, id DESC
),
previous_summary AS (
  SELECT DISTINCT ON (repo_full_name)
         repo_full_name, id AS prev_id, readme_sha AS prev_sha, summary_ko, summary_ko_updated_at
  FROM repo_readme_cache
  WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> ''
  ORDER BY repo_full_name, summary_ko_updated_at DESC NULLS LAST, id DESC
)
SELECT
  l.repo_full_name,
  l.id AS latest_id,
  l.readme_sha AS latest_sha,
  p.prev_id,
  p.prev_sha,
  CASE WHEN l.readme_sha = p.prev_sha THEN 'same_sha' ELSE 'different_sha' END AS sha_relation,
  p.summary_ko_updated_at
FROM latest l
JOIN previous_summary p USING (repo_full_name)
WHERE l.summary_ko IS NULL OR BTRIM(l.summary_ko) = ''
ORDER BY l.repo_full_name;

-- count by sha relation for fallback candidates
WITH latest AS (
  SELECT DISTINCT ON (repo_full_name)
         repo_full_name, readme_sha, summary_ko
  FROM repo_readme_cache
  ORDER BY repo_full_name, readme_fetched_at DESC, id DESC
),
previous_summary AS (
  SELECT DISTINCT ON (repo_full_name)
         repo_full_name, readme_sha AS prev_sha
  FROM repo_readme_cache
  WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> ''
  ORDER BY repo_full_name, summary_ko_updated_at DESC NULLS LAST, id DESC
)
SELECT
  CASE WHEN l.readme_sha = p.prev_sha THEN 'same_sha' ELSE 'different_sha' END AS sha_relation,
  COUNT(*) AS repo_count
FROM latest l
JOIN previous_summary p USING (repo_full_name)
WHERE l.summary_ko IS NULL OR BTRIM(l.summary_ko) = ''
GROUP BY 1
ORDER BY 1;

-- ============================================================
-- 3) ingestion shape checks
-- ============================================================
-- rows where readme_text exists but is effectively empty
SELECT
  COUNT(*) AS bad_readme_text_rows
FROM repo_readme_cache
WHERE readme_text IS NULL OR BTRIM(readme_text) = '';

-- possible ordering collision: same repo + same fetched_at with multiple rows
SELECT
  repo_full_name,
  readme_fetched_at,
  COUNT(*) AS row_count
FROM repo_readme_cache
GROUP BY repo_full_name, readme_fetched_at
HAVING COUNT(*) > 1
ORDER BY row_count DESC, repo_full_name, readme_fetched_at DESC
LIMIT 200;

-- ============================================================
-- 4) optional remediation (safe)
-- copy summary only when latest row has same SHA as a summarized row
-- ============================================================
-- BEGIN;
WITH latest AS (
  SELECT DISTINCT ON (repo_full_name)
         id, repo_full_name, readme_sha, summary_ko
  FROM repo_readme_cache
  ORDER BY repo_full_name, readme_fetched_at DESC, id DESC
),
source_same_sha AS (
  SELECT DISTINCT ON (repo_full_name, readme_sha)
         repo_full_name, readme_sha, summary_ko, summary_ko_model
  FROM repo_readme_cache
  WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> ''
  ORDER BY repo_full_name, readme_sha, summary_ko_updated_at DESC NULLS LAST, id DESC
)
UPDATE repo_readme_cache t
SET summary_ko = s.summary_ko,
    summary_ko_model = COALESCE(t.summary_ko_model, s.summary_ko_model, 'cache-backfill-same-sha'),
    summary_ko_updated_at = CURRENT_TIMESTAMP
FROM latest l
JOIN source_same_sha s
  ON s.repo_full_name = l.repo_full_name
 AND s.readme_sha = l.readme_sha
WHERE t.id = l.id
  AND (t.summary_ko IS NULL OR BTRIM(t.summary_ko) = '');
-- COMMIT;

-- ============================================================
-- 5) optional remediation (aggressive, review first)
-- fill latest summary from most recent summary of same repo even if SHA changed
-- use only if your policy allows stale-summary fallback persistence
-- ============================================================
-- BEGIN;
WITH latest AS (
  SELECT DISTINCT ON (repo_full_name)
         id, repo_full_name, readme_sha, summary_ko
  FROM repo_readme_cache
  ORDER BY repo_full_name, readme_fetched_at DESC, id DESC
),
source_any AS (
  SELECT DISTINCT ON (repo_full_name)
         repo_full_name, readme_sha AS source_sha, summary_ko, summary_ko_model
  FROM repo_readme_cache
  WHERE summary_ko IS NOT NULL AND BTRIM(summary_ko) <> ''
  ORDER BY repo_full_name, summary_ko_updated_at DESC NULLS LAST, id DESC
)
UPDATE repo_readme_cache t
SET summary_ko = s.summary_ko,
    summary_ko_model = COALESCE(t.summary_ko_model, s.summary_ko_model, 'cache-backfill-any-sha'),
    summary_ko_updated_at = CURRENT_TIMESTAMP
FROM latest l
JOIN source_any s ON s.repo_full_name = l.repo_full_name
WHERE t.id = l.id
  AND (t.summary_ko IS NULL OR BTRIM(t.summary_ko) = '');
-- COMMIT;
