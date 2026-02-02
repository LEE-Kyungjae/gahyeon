CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS weather_rag_chunks (
    id BIGSERIAL PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    city_name VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_date DATE NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_rag_city_source_date
    ON weather_rag_chunks(city, source_type, source_date);

CREATE INDEX IF NOT EXISTS idx_weather_rag_source_date
    ON weather_rag_chunks(source_date DESC);

CREATE INDEX IF NOT EXISTS idx_weather_rag_embedding
    ON weather_rag_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON TABLE weather_rag_chunks IS 'pgvector 기반 날씨 RAG 청크 저장소';
COMMENT ON COLUMN weather_rag_chunks.source_type IS 'current 또는 forecast';
COMMENT ON COLUMN weather_rag_chunks.source_date IS '현재/예보 데이터 기준 날짜';
COMMENT ON COLUMN weather_rag_chunks.chunk_text IS '임베딩 대상 원문 청크';
COMMENT ON COLUMN weather_rag_chunks.embedding IS 'OpenAI 임베딩 벡터(1536)';
