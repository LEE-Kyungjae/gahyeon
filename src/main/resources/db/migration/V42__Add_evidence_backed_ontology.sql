-- Claims stay attached to source chunks: hard deletion cascades; soft deletion is checked at retrieval.
CREATE TABLE knowledge_ontology_claims (
    id VARCHAR(64) PRIMARY KEY,
    chunk_id VARCHAR(36) NOT NULL REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    subject_key VARCHAR(160) NOT NULL,
    subject_type VARCHAR(32) NOT NULL,
    subject_label VARCHAR(160) NOT NULL,
    subject_aliases TEXT NOT NULL,
    relation_type VARCHAR(32) NOT NULL,
    object_key VARCHAR(160) NOT NULL,
    object_type VARCHAR(32) NOT NULL,
    object_label VARCHAR(160) NOT NULL,
    object_aliases TEXT NOT NULL,
    evidence_quote VARCHAR(600) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ontology_claim_chunk ON knowledge_ontology_claims(chunk_id);
CREATE INDEX idx_ontology_claim_subject ON knowledge_ontology_claims(subject_type, subject_key);
CREATE INDEX idx_ontology_claim_object ON knowledge_ontology_claims(object_type, object_key);
