-- 대화 히스토리 테이블 (사용자별 대화 맥락 유지)
CREATE TABLE conversation_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT,
    summary TEXT,
    summarized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_conv_user_id ON conversation_history(user_id);
CREATE INDEX idx_conv_created_at ON conversation_history(created_at);
CREATE INDEX idx_conv_user_created ON conversation_history(user_id, created_at DESC);

COMMENT ON TABLE conversation_history IS '사용자별 AI 대화 히스토리';
COMMENT ON COLUMN conversation_history.user_id IS 'Discord 사용자 ID';
COMMENT ON COLUMN conversation_history.user_message IS '사용자 메시지';
COMMENT ON COLUMN conversation_history.ai_response IS 'AI 응답';
COMMENT ON COLUMN conversation_history.summary IS '요약된 대화 내용 (GLM으로 생성)';
COMMENT ON COLUMN conversation_history.summarized IS '요약 완료 여부';
