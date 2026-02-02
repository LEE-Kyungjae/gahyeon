-- 하이브리드 검색(BM25 유사 full-text + vector)을 위한 GIN 인덱스
CREATE INDEX IF NOT EXISTS idx_weather_rag_chunk_text_fts
    ON weather_rag_chunks
    USING gin (to_tsvector('simple', chunk_text));
