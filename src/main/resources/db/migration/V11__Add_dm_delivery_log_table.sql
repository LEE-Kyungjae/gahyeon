CREATE TABLE IF NOT EXISTS dm_delivery_log (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(120) NOT NULL,
    dedupe_key VARCHAR(200) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    attempted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dm_delivery_log_run_id ON dm_delivery_log(run_id);
CREATE INDEX IF NOT EXISTS idx_dm_delivery_log_user_id ON dm_delivery_log(user_id);
CREATE INDEX IF NOT EXISTS idx_dm_delivery_log_attempted_at ON dm_delivery_log(attempted_at);

COMMENT ON TABLE dm_delivery_log IS '정기 개인 메시지 발송 로그';
COMMENT ON COLUMN dm_delivery_log.run_id IS '배치 실행 ID';
COMMENT ON COLUMN dm_delivery_log.dedupe_key IS '중복 발송 방지 키';
COMMENT ON COLUMN dm_delivery_log.user_id IS 'Discord 사용자 ID';
COMMENT ON COLUMN dm_delivery_log.content_hash IS '메시지 본문 해시';
COMMENT ON COLUMN dm_delivery_log.status IS '발송 상태';
COMMENT ON COLUMN dm_delivery_log.error_message IS '실패 사유';
COMMENT ON COLUMN dm_delivery_log.attempted_at IS '발송 시도 시각';
