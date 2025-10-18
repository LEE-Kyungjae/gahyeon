-- OpenAI 사용 내역 테이블에 interaction_id 컬럼 추가
-- 여러 봇 인스턴스 병렬 실행 시 중복 방지용

-- 1. 먼저 NULL 허용으로 컬럼 추가
ALTER TABLE openai_usage
ADD COLUMN interaction_id VARCHAR(100);

-- 2. 기존 데이터에 임시 고유 ID 부여 (UPDATE 문 사용)
UPDATE openai_usage
SET interaction_id = 'migration-' || id::TEXT
WHERE interaction_id IS NULL;

-- 3. NOT NULL 제약조건 추가
ALTER TABLE openai_usage
ALTER COLUMN interaction_id SET NOT NULL;

-- 4. UNIQUE 제약조건 추가
ALTER TABLE openai_usage
ADD CONSTRAINT uk_interaction_id UNIQUE (interaction_id);

-- 5. 인덱스는 UNIQUE 제약조건이 자동으로 생성

-- 테이블 코멘트
COMMENT ON COLUMN openai_usage.interaction_id IS 'Discord Interaction ID (여러 인스턴스 병렬 실행 시 중복 방지)';
