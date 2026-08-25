CREATE TABLE knowledge_sources (
    id VARCHAR(36) PRIMARY KEY,
    service_id VARCHAR(64) NOT NULL,
    owner_subject_id VARCHAR(160),
    source_type VARCHAR(32) NOT NULL,
    display_name VARCHAR(240) NOT NULL,
    source_uri VARCHAR(2048),
    access_scope VARCHAR(24) NOT NULL CHECK (access_scope IN ('PUBLIC', 'SERVICE', 'PRIVATE')),
    lifecycle_status VARCHAR(24) NOT NULL CHECK (lifecycle_status IN ('ACTIVE', 'DISABLED', 'DELETED')),
    content_sha256 VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT ck_knowledge_source_private_owner
        CHECK (access_scope <> 'PRIVATE' OR owner_subject_id IS NOT NULL)
);

CREATE TABLE knowledge_documents (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(36) NOT NULL REFERENCES knowledge_sources(id),
    service_id VARCHAR(64) NOT NULL,
    owner_subject_id VARCHAR(160),
    title VARCHAR(500) NOT NULL,
    language VARCHAR(16) NOT NULL DEFAULT 'ko',
    body_text TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    content_sha256 VARCHAR(64) NOT NULL,
    version BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (source_id, content_sha256)
);

CREATE TABLE knowledge_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES knowledge_documents(id),
    source_id VARCHAR(36) NOT NULL REFERENCES knowledge_sources(id),
    service_id VARCHAR(64) NOT NULL,
    owner_subject_id VARCHAR(160),
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_model VARCHAR(160),
    embedding_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (document_id, ordinal)
);

CREATE INDEX idx_knowledge_source_authorization
    ON knowledge_sources (service_id, owner_subject_id, access_scope, lifecycle_status);
CREATE INDEX idx_knowledge_document_authorization
    ON knowledge_documents (service_id, owner_subject_id, deleted_at);
CREATE INDEX idx_knowledge_chunk_authorization
    ON knowledge_chunks (service_id, owner_subject_id, source_id, deleted_at);

CREATE TABLE memory_identity_merge_requests (
    id VARCHAR(36) PRIMARY KEY,
    principal_id BIGINT NOT NULL REFERENCES gahyeon_principals(id),
    source_subject_id VARCHAR(160) NOT NULL,
    target_subject_id VARCHAR(160) NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED')),
    approval_digest VARCHAR(64),
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    decided_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_class VARCHAR(120),
    UNIQUE (source_subject_id, target_subject_id)
);

CREATE TABLE privacy_deletion_jobs (
    id VARCHAR(36) PRIMARY KEY,
    service_id VARCHAR(64) NOT NULL,
    subject_id VARCHAR(160) NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    postgres_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    vector_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    cache_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    derived_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_class VARCHAR(120)
);

CREATE INDEX idx_privacy_deletion_subject
    ON privacy_deletion_jobs (service_id, subject_id, status);

CREATE TABLE character_identity_revisions (
    id VARCHAR(36) PRIMARY KEY,
    character_id VARCHAR(64) NOT NULL,
    revision BIGINT NOT NULL,
    soul_markdown TEXT NOT NULL,
    created_by_subject_id VARCHAR(160) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    activated_at TIMESTAMP WITH TIME ZONE,
    retired_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (character_id, revision)
);

CREATE TABLE character_autonomy_todos (
    id VARCHAR(36) PRIMARY KEY,
    character_id VARCHAR(64) NOT NULL,
    world_id VARCHAR(100) NOT NULL,
    owner_subject_id VARCHAR(160),
    description VARCHAR(1000) NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'CANCELLED', 'BLOCKED')),
    not_before TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_character_autonomy_due
    ON character_autonomy_todos (character_id, world_id, status, not_before);

CREATE TABLE memory_graph_nodes (
    id VARCHAR(36) PRIMARY KEY,
    character_id VARCHAR(64) NOT NULL,
    world_id VARCHAR(100) NOT NULL,
    owner_subject_id VARCHAR(160) NOT NULL,
    node_type VARCHAR(32) NOT NULL,
    node_key VARCHAR(240) NOT NULL,
    label VARCHAR(500) NOT NULL,
    properties_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (character_id, world_id, owner_subject_id, node_type, node_key)
);

CREATE TABLE memory_graph_edges (
    id VARCHAR(36) PRIMARY KEY,
    character_id VARCHAR(64) NOT NULL,
    world_id VARCHAR(100) NOT NULL,
    owner_subject_id VARCHAR(160) NOT NULL,
    from_node_id VARCHAR(36) NOT NULL REFERENCES memory_graph_nodes(id),
    to_node_id VARCHAR(36) NOT NULL REFERENCES memory_graph_nodes(id),
    relation_type VARCHAR(64) NOT NULL,
    weight DOUBLE PRECISION NOT NULL CHECK (weight >= 0 AND weight <= 1),
    evidence_memory_id BIGINT REFERENCES character_memories(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (owner_subject_id, from_node_id, to_node_id, relation_type)
);

CREATE INDEX idx_memory_graph_node_scope
    ON memory_graph_nodes (character_id, world_id, owner_subject_id, node_type);
CREATE INDEX idx_memory_graph_edge_scope
    ON memory_graph_edges (character_id, world_id, owner_subject_id, relation_type);

CREATE TABLE character_heartbeat_runs (
    id VARCHAR(36) PRIMARY KEY,
    character_id VARCHAR(64) NOT NULL,
    world_id VARCHAR(100) NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('STARTED', 'COMPLETED', 'FAILED', 'NO_WORK')),
    claimed_todo_id VARCHAR(36) REFERENCES character_autonomy_todos(id),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_class VARCHAR(120)
);

CREATE INDEX idx_character_heartbeat_recent
    ON character_heartbeat_runs (character_id, world_id, started_at DESC);
