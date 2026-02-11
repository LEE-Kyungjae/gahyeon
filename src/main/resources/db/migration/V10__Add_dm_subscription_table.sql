CREATE TABLE IF NOT EXISTS dm_subscription (
    user_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Seoul',
    opted_in_at TIMESTAMP,
    opted_out_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dm_subscription_enabled ON dm_subscription(enabled);

COMMENT ON TABLE dm_subscription IS '정기 개인 메시지 수신 동의 상태';
COMMENT ON COLUMN dm_subscription.user_id IS 'Discord 사용자 ID';
COMMENT ON COLUMN dm_subscription.enabled IS '수신 동의 여부';
COMMENT ON COLUMN dm_subscription.timezone IS '수신 시간대';
COMMENT ON COLUMN dm_subscription.opted_in_at IS '수신 동의 시각';
COMMENT ON COLUMN dm_subscription.opted_out_at IS '수신 거부 시각';
COMMENT ON COLUMN dm_subscription.created_at IS '레코드 생성 시각';
COMMENT ON COLUMN dm_subscription.updated_at IS '레코드 갱신 시각';
