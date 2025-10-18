-- OpenAI 사용 내역 테이블에 interaction_id 컬럼 추가
-- 여러 봇 인스턴스 병렬 실행 시 중복 방지용

ALTER TABLE openai_usage
ADD COLUMN interaction_id VARCHAR(100) UNIQUE NOT NULL DEFAULT 'migration-' || id::TEXT;

-- 기본값 제거 (새 레코드는 반드시 interaction_id 제공)
ALTER TABLE openai_usage
ALTER COLUMN interaction_id DROP DEFAULT;

-- 인덱스 생성 (중복 체크 성능 향상)
CREATE INDEX IF NOT EXISTS idx_interaction_id ON openai_usage(interaction_id);

-- 테이블 코멘트
COMMENT ON COLUMN openai_usage.interaction_id IS 'Discord Interaction ID (여러 인스턴스 병렬 실행 시 중복 방지)';
