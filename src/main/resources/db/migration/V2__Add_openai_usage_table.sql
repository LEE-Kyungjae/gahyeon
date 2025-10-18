-- OpenAI API 사용 내역 테이블 생성
CREATE TABLE IF NOT EXISTS openai_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(100) NOT NULL,
    guild_id BIGINT,
    prompt TEXT NOT NULL,
    response TEXT,
    prompt_tokens INTEGER,
    response_tokens INTEGER,
    total_tokens INTEGER,
    model VARCHAR(50),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성 (Rate Limiting 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_user_id ON openai_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON openai_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_user_created ON openai_usage(user_id, created_at);

-- 테이블 코멘트
COMMENT ON TABLE openai_usage IS 'OpenAI API 사용 내역 추적 (비용 관리 및 Rate Limiting용)';
COMMENT ON COLUMN openai_usage.user_id IS 'Discord 사용자 ID';
COMMENT ON COLUMN openai_usage.username IS 'Discord 사용자 이름';
COMMENT ON COLUMN openai_usage.guild_id IS 'Discord 서버 ID';
COMMENT ON COLUMN openai_usage.prompt IS '사용자 질문 (원본)';
COMMENT ON COLUMN openai_usage.response IS 'AI 응답 (원본)';
COMMENT ON COLUMN openai_usage.prompt_tokens IS '프롬프트 토큰 수';
COMMENT ON COLUMN openai_usage.response_tokens IS '응답 토큰 수';
COMMENT ON COLUMN openai_usage.total_tokens IS '전체 토큰 수';
COMMENT ON COLUMN openai_usage.model IS '사용된 모델 (예: gpt-4o-mini)';
COMMENT ON COLUMN openai_usage.success IS '요청 성공 여부';
COMMENT ON COLUMN openai_usage.error_message IS '에러 메시지 (실패 시)';
COMMENT ON COLUMN openai_usage.created_at IS '생성 시간';
