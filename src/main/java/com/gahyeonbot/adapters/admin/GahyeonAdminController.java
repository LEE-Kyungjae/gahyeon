package com.gahyeonbot.adapters.admin;

import com.gahyeonbot.application.knowledge.KnowledgeBaseService;
import com.gahyeonbot.application.life.CharacterAutonomyWorkspaceService;
import com.gahyeonbot.application.privacy.MemoryGovernanceService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/admin/gahyeon")
public class GahyeonAdminController {
    private final GahyeonAdminAuthorization authorization;
    private final KnowledgeBaseService knowledge;
    private final MemoryGovernanceService governance;
    private final CharacterAutonomyWorkspaceService workspace;
    private final JdbcTemplate jdbc;

    public GahyeonAdminController(GahyeonAdminAuthorization authorization, KnowledgeBaseService knowledge,
            MemoryGovernanceService governance, CharacterAutonomyWorkspaceService workspace, JdbcTemplate jdbc) {
        this.authorization = authorization;
        this.knowledge = knowledge;
        this.governance = governance;
        this.workspace = workspace;
        this.jdbc = jdbc;
    }

    @GetMapping("/overview")
    public Map<String, Object> overview(HttpServletRequest request) {
        authorization.require(request);
        return Map.of(
                "knowledgeSources", count("knowledge_sources", "lifecycle_status = 'ACTIVE'"),
                "knowledgeDocuments", count("knowledge_documents", "deleted_at is null"),
                "knowledgeChunks", count("knowledge_chunks", "deleted_at is null"),
                "memories", count("character_memories", "superseded_at is null"),
                "pendingMerges", count("memory_identity_merge_requests", "status = 'PENDING'"),
                "pendingTodos", count("character_autonomy_todos", "status = 'PENDING'"));
    }

    @PostMapping("/knowledge")
    public KnowledgeBaseService.IngestionResult ingest(@RequestBody KnowledgeIngestBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return knowledge.ingest(new KnowledgeBaseService.IngestionRequest(body.serviceId(), body.ownerSubjectId(),
                body.sourceType(), body.displayName(), body.sourceUri(), body.accessScope(), body.title(),
                body.language(), body.bodyText(), body.metadataJson()));
    }

    @PostMapping("/knowledge/search")
    public List<KnowledgeBaseService.SearchResult> search(@RequestBody KnowledgeSearchBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return knowledge.search(new KnowledgeBaseService.SearchRequest(
                body.serviceId(), body.subjectId(), body.query(), body.limit()));
    }

    @DeleteMapping("/knowledge/{sourceId}")
    public void deleteKnowledge(@PathVariable String sourceId, @RequestParam String serviceId,
            @RequestParam(required = false) String subjectId, HttpServletRequest request) {
        authorization.require(request);
        knowledge.softDeleteSource(serviceId, subjectId, sourceId);
    }

    @PostMapping("/memory/merge-requests")
    public MemoryGovernanceService.MergeRequest requestMerge(@RequestBody MergeRequestBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return governance.requestMerge(body.principalId(), body.sourceSubjectId(), body.targetSubjectId());
    }

    @PostMapping("/memory/merge-requests/{id}/approve")
    public void approveMerge(@PathVariable String id, @RequestBody ApprovalBody body, HttpServletRequest request) {
        authorization.require(request);
        governance.approveMerge(id, body.userApprovalProof());
    }

    @PostMapping("/memory/merge-requests/{id}/execute")
    public MemoryGovernanceService.MergeResult executeMerge(@PathVariable String id, HttpServletRequest request) {
        authorization.require(request);
        return governance.executeApprovedMerge(id);
    }

    @PostMapping("/privacy/delete")
    public MemoryGovernanceService.DeletionResult deleteSubject(@RequestBody DeleteSubjectBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return governance.deleteSubject(body.principalId(), body.serviceId(), body.subjectId());
    }

    @PostMapping("/soul/revisions")
    public CharacterAutonomyWorkspaceService.SoulRevision createSoul(@RequestBody SoulBody body,
            HttpServletRequest request) {
        authorization.require(request);
        return workspace.createSoulRevision(body.characterId(), body.soulMarkdown(), body.createdBySubjectId());
    }

    @PostMapping("/soul/{characterId}/{revision}/activate")
    public void activateSoul(@PathVariable String characterId, @PathVariable long revision,
            HttpServletRequest request) {
        authorization.require(request);
        workspace.activateSoulRevision(characterId, revision);
    }

    @PostMapping("/todos")
    public CharacterAutonomyWorkspaceService.Todo addTodo(@RequestBody TodoBody body, HttpServletRequest request) {
        authorization.require(request);
        return workspace.addTodo(body.characterId(), body.worldId(), body.ownerSubjectId(), body.description());
    }

    private long count(String table, String predicate) {
        Long value = jdbc.queryForObject("select count(*) from " + table + " where " + predicate, Long.class);
        return value == null ? 0 : value;
    }

    public record KnowledgeIngestBody(String serviceId, String ownerSubjectId, String sourceType,
            String displayName, String sourceUri, KnowledgeBaseService.AccessScope accessScope, String title,
            String language, String bodyText, String metadataJson) {}
    public record KnowledgeSearchBody(String serviceId, String subjectId, String query, int limit) {}
    public record MergeRequestBody(long principalId, String sourceSubjectId, String targetSubjectId) {}
    public record ApprovalBody(String userApprovalProof) {}
    public record DeleteSubjectBody(long principalId, String serviceId, String subjectId) {}
    public record SoulBody(String characterId, String soulMarkdown, String createdBySubjectId) {}
    public record TodoBody(String characterId, String worldId, String ownerSubjectId, String description) {}
}
