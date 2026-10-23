package com.gahyeonbot.application.knowledge;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Objects;

@Service
public class OntologyIngestionService {
    private final KnowledgeBaseService knowledge;
    private final OntologyGraphService graph;
    private final JdbcTemplate jdbc;

    public OntologyIngestionService(KnowledgeBaseService knowledge, OntologyGraphService graph, JdbcTemplate jdbc) {
        this.knowledge = knowledge;
        this.graph = graph;
        this.jdbc = jdbc;
    }

    @Transactional
    public Result ingest(KnowledgeBaseService.IngestionRequest document, OntologySchema.Document ontology) {
        Objects.requireNonNull(document);
        Objects.requireNonNull(ontology);
        var result = knowledge.ingest(document);
        // Legacy deduplication uses text/owner; never attach a private ontology to a public duplicate.
        String scope = jdbc.queryForObject("""
                select s.access_scope from knowledge_documents d join knowledge_sources s on s.id = d.source_id
                where d.id = ?
                """, String.class, result.documentId());
        if (!document.accessScope().name().equals(scope))
            throw new IllegalArgumentException("Duplicate document has a different access scope; explicit source review required");
        int count = graph.index(document.serviceId(), document.ownerSubjectId(), result.documentId(), ontology);
        return new Result(result.documentId(), result.chunkCount(), result.duplicate(), count);
    }

    public record Result(String documentId, int chunksCreated, boolean duplicateDocument, int claimsIndexed) {}
}
