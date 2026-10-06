package com.gahyeonbot.adapters.admin;

import com.gahyeonbot.application.knowledge.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/admin/gahyeon/ontology")
@ConditionalOnProperty(name = "gahyeon.ontology.enabled", havingValue = "true")
public class OntologyAdminController {
    private final GahyeonAdminAuthorization authorization;
    private final OntologyIngestionService ingestion;
    private final OntologyGraphService graph;
    private final OntologyRagService rag;

    public OntologyAdminController(GahyeonAdminAuthorization authorization, OntologyIngestionService ingestion,
            OntologyGraphService graph, OntologyRagService rag) {
        this.authorization = authorization;
        this.ingestion = ingestion;
        this.graph = graph;
        this.rag = rag;
    }

    @GetMapping("/schema")
    public Map<String, Object> schema(HttpServletRequest request) {
        authorization.require(request);
        return Map.of("schemaVersion", 1, "relations", OntologySchema.definitions());
    }

    @PostMapping("/ingest")
    public OntologyIngestionService.Result ingest(@RequestBody IngestBody body, HttpServletRequest request) {
        authorization.require(request);
        return ingestion.ingest(body.document(), body.ontology());
    }

    @PostMapping("/documents/{documentId}")
    public Map<String, Integer> index(@PathVariable String documentId, @RequestBody IndexBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return Map.of("claimsIndexed", graph.index(body.serviceId(), body.ownerSubjectId(), documentId, body.ontology()));
    }

    @PostMapping("/graph/search")
    public OntologyGraphService.SearchReport graphSearch(@RequestBody OntologyGraphService.Query body,
            HttpServletRequest request) {
        authorization.require(request);
        return graph.search(body);
    }

    @PostMapping("/search")
    public OntologyRagService.Result search(@RequestBody KnowledgeBaseService.SearchRequest body,
            HttpServletRequest request) {
        authorization.require(request);
        return rag.search(body);
    }

    @ExceptionHandler({IllegalArgumentException.class, NullPointerException.class})
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String, String> invalidInput() { return Map.of("error", "Invalid ontology request"); }

    @ExceptionHandler(java.util.NoSuchElementException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Map<String, String> unavailableDocument() { return Map.of("error", "Ontology document not available"); }

    public record IngestBody(KnowledgeBaseService.IngestionRequest document, OntologySchema.Document ontology) {}
    public record IndexBody(String serviceId, String ownerSubjectId, OntologySchema.Document ontology) {}
}
