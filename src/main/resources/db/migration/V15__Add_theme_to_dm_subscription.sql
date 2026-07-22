-- 테마별 DM 구독으로 확장: (user_id) 단일 PK -> (user_id, theme) 복합 PK.
-- 기존 구독자는 GitHub 트렌딩 구독으로 보존된다.

ALTER TABLE dm_subscription
    ADD COLUMN IF NOT EXISTS theme VARCHAR(50) NOT NULL DEFAULT 'GITHUB_TRENDING';

ALTER TABLE dm_subscription DROP CONSTRAINT IF EXISTS dm_subscription_pkey;
ALTER TABLE dm_subscription ADD PRIMARY KEY (user_id, theme);

-- 테마별 활성 구독자 조회용 인덱스.
CREATE INDEX IF NOT EXISTS idx_dm_subscription_theme_enabled
    ON dm_subscription(theme, enabled);

COMMENT ON COLUMN dm_subscription.theme IS '뉴스레터 테마 (NewsletterTheme enum)';
