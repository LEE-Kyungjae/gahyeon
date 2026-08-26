package com.gahyeonbot.application.knowledge;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class KnowledgeBaseService {
    private static final int CHUNK_CHARACTERS = 1_200;
    private static final int CHUNK_OVERLAP = 150;
    private static final int MAX_CANDIDATES = 500;
    private final JdbcTemplate jdbc;
    private final ObjectProvider<KnowledgeEmbeddingPort> embeddings;
    private final ObjectMapper json;
    private final Clock clock;

    @Autowired
    public KnowledgeBaseService(JdbcTemplate jdbc, ObjectProvider<KnowledgeEmbeddingPort> embeddings,
            ObjectMapper json) {
        this(jdbc, embeddings, json, Clock.systemUTC());
    }

    KnowledgeBaseService(JdbcTemplate jdbc, ObjectProvider<KnowledgeEmbeddingPort> embeddings,
            ObjectMapper json, Clock clock) {
        this.jdbc = jdbc;
        this.embeddings = embeddings;
        this.json = json;
        this.clock = clock;
    }

    @Transactional
    public IngestionResult ingest(IngestionRequest request) {
        request.validate();
        String normalized = normalize(request.bodyText());
        String digest = sha256(normalized);
        String existing = jdbc.query("""
                select d.id from knowledge_documents d join knowledge_sources s on s.id = d.source_id
                where s.service_id = ? and s.lifecycle_status = 'ACTIVE' and d.content_sha256 = ?
                  and ((? is null and s.owner_subject_id is null) or s.owner_subject_id = ?)
                  and d.deleted_at is null fetch first 1 row only
                """, rs -> rs.next() ? rs.getString(1) : null,
                request.serviceId(), digest, request.ownerSubjectId(), request.ownerSubjectId());
        if (existing != null) return new IngestionResult(existing, 0, true);

        String sourceId = UUID.randomUUID().toString();
        String documentId = UUID.randomUUID().toString();
        OffsetDateTime now = OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
        jdbc.update("""
                insert into knowledge_sources
                (id, service_id, owner_subject_id, source_type, display_name, source_uri, access_scope,
                 lifecycle_status, content_sha256, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """, sourceId, request.serviceId(), request.ownerSubjectId(), request.sourceType(),
                request.displayName(), request.sourceUri(), request.accessScope().name(), digest, now, now);
        jdbc.update("""
                insert into knowledge_documents
                (id, source_id, service_id, owner_subject_id, title, language, body_text, metadata_json,
                 content_sha256, version, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, documentId, sourceId, request.serviceId(), request.ownerSubjectId(), request.title(),
                request.language(), normalized, request.metadataJson(), digest, now, now);

        KnowledgeEmbeddingPort embedder = embeddings.getIfAvailable();
        List<String> chunks = chunks(normalized);
        for (int ordinal = 0; ordinal < chunks.size(); ordinal++) {
            String content = chunks.get(ordinal);
            List<Double> vector = embedder != null && embedder.isReady() ? embedder.embed(content) : List.of();
            jdbc.update("""
                    insert into knowledge_chunks
                    (id, document_id, source_id, service_id, owner_subject_id, ordinal, content, token_count,
                     embedding_model, embedding_json, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, UUID.randomUUID().toString(), documentId, sourceId, request.serviceId(),
                    request.ownerSubjectId(), ordinal, content, approximateTokens(content),
                    vector.isEmpty() ? null : embedder.modelId(), vector.isEmpty() ? null : writeJson(vector), now);
        }
        return new IngestionResult(documentId, chunks.size(), false);
    }

    public List<SearchResult> search(SearchRequest request) {
        request.validate();
        List<Candidate> candidates = jdbc.query("""
                select c.id, c.document_id, c.source_id, d.title, c.content, c.embedding_model, c.embedding_json
                from knowledge_chunks c
                join knowledge_documents d on d.id = c.document_id
                join knowledge_sources s on s.id = c.source_id
                where c.service_id = ? and d.service_id = ? and s.service_id = ?
                  and c.deleted_at is null and d.deleted_at is null and s.deleted_at is null
                  and s.lifecycle_status = 'ACTIVE'
                  and (s.access_scope in ('PUBLIC', 'SERVICE')
                       or (s.access_scope = 'PRIVATE' and s.owner_subject_id = ? and c.owner_subject_id = ?))
                order by c.created_at desc fetch first 500 rows only
                """, (rs, row) -> new Candidate(rs.getString("id"), rs.getString("document_id"),
                        rs.getString("source_id"), rs.getString("title"), rs.getString("content"),
                        rs.getString("embedding_model"), rs.getString("embedding_json")),
                request.serviceId(), request.serviceId(), request.serviceId(),
                request.subjectId(), request.subjectId());
        if (candidates.size() > MAX_CANDIDATES) candidates = candidates.subList(0, MAX_CANDIDATES);
        KnowledgeEmbeddingPort embedder = embeddings.getIfAvailable();
        List<Double> queryVector = embedder != null && embedder.isReady() ? embedder.embed(request.query()) : List.of();
        Set<String> terms = terms(request.query());
        String normalizedQuery = searchable(request.query());
        return candidates.stream()
                .map(candidate -> score(candidate, terms, normalizedQuery, queryVector))
                .filter(result -> result.score() > 0)
                .sorted(Comparator.comparingDouble(SearchResult::score).reversed()
                        .thenComparing(SearchResult::chunkId))
                .limit(request.limit())
                .toList();
    }

    @Transactional
    public void softDeleteSource(String serviceId, String subjectId, String sourceId) {
        int changed = jdbc.update("""
                update knowledge_sources set lifecycle_status = 'DELETED', deleted_at = current_timestamp,
                    updated_at = current_timestamp
                where id = ? and service_id = ? and ((access_scope <> 'PRIVATE') or owner_subject_id = ?)
                """, sourceId, serviceId, subjectId);
        if (changed != 1) throw new NoSuchElementException("authorized knowledge source not found");
        jdbc.update("update knowledge_documents set deleted_at = current_timestamp where source_id = ?", sourceId);
        jdbc.update("update knowledge_chunks set deleted_at = current_timestamp where source_id = ?", sourceId);
    }

    private SearchResult score(Candidate candidate, Set<String> terms, String normalizedQuery,
            List<Double> queryVector) {
        String title = searchable(candidate.title());
        String content = searchable(candidate.content());
        long contentMatches = terms.stream().filter(content::contains).count();
        long titleMatches = terms.stream().filter(title::contains).count();
        double coverage = terms.isEmpty() ? 0 : (double) contentMatches / terms.size();
        double titleCoverage = terms.isEmpty() ? 0 : (double) titleMatches / terms.size();
        boolean phraseMatch = normalizedQuery.length() >= 4
                && (title.contains(normalizedQuery) || content.contains(normalizedQuery));
        double lexical = Math.min(1, coverage * 0.70 + titleCoverage * 0.20 + (phraseMatch ? 0.10 : 0));
        double semantic = queryVector.isEmpty() ? 0 : cosine(queryVector, readVector(candidate.embeddingJson()));
        double score = queryVector.isEmpty() ? lexical : lexical * 0.45 + Math.max(0, semantic) * 0.55;
        return new SearchResult(candidate.id(), candidate.documentId(), candidate.sourceId(), candidate.title(),
                candidate.content(), score, lexical, semantic);
    }

    static List<String> chunks(String text) {
        if (text.length() <= CHUNK_CHARACTERS) return List.of(text);
        List<String> result = new ArrayList<>();
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(text.length(), start + CHUNK_CHARACTERS);
            if (end < text.length()) {
                int boundary = Math.max(text.lastIndexOf('\n', end), text.lastIndexOf(' ', end));
                if (boundary > start + CHUNK_CHARACTERS / 2) end = boundary;
            }
            result.add(text.substring(start, end).trim());
            if (end == text.length()) break;
            start = Math.max(start + 1, end - CHUNK_OVERLAP);
        }
        return result.stream().filter(value -> !value.isBlank()).toList();
    }

    private List<Double> readVector(String value) {
        if (value == null || value.isBlank()) return List.of();
        try { return json.readValue(value, new TypeReference<>() {}); }
        catch (JsonProcessingException ignored) { return List.of(); }
    }

    private String writeJson(List<Double> value) {
        try { return json.writeValueAsString(value); }
        catch (JsonProcessingException failure) { throw new IllegalStateException("embedding serialization failed", failure); }
    }

    private static double cosine(List<Double> left, List<Double> right) {
        if (left.isEmpty() || left.size() != right.size()) return 0;
        double dot = 0, leftNorm = 0, rightNorm = 0;
        for (int i = 0; i < left.size(); i++) {
            dot += left.get(i) * right.get(i);
            leftNorm += left.get(i) * left.get(i);
            rightNorm += right.get(i) * right.get(i);
        }
        return leftNorm == 0 || rightNorm == 0 ? 0 : dot / Math.sqrt(leftNorm * rightNorm);
    }

    private static Set<String> terms(String query) {
        return new LinkedHashSet<>(Arrays.stream(query.toLowerCase(Locale.ROOT).split("[^\\p{L}\\p{N}]+"))
                .filter(term -> term.length() > 1).toList());
    }

    private static String searchable(String value) {
        return value.toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]+", " ").trim();
    }

    private static String normalize(String value) { return value.trim().replace("\r\n", "\n"); }
    private static int approximateTokens(String value) { return Math.max(1, (int) Math.ceil(value.length() / 3.2)); }
    private static String sha256(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception impossible) { throw new IllegalStateException(impossible); }
    }

    public enum AccessScope { PUBLIC, SERVICE, PRIVATE }

    public record IngestionRequest(String serviceId, String ownerSubjectId, String sourceType, String displayName,
            String sourceUri, AccessScope accessScope, String title, String language, String bodyText,
            String metadataJson) {
        void validate() {
            if (blank(serviceId) || blank(sourceType) || blank(displayName) || accessScope == null
                    || blank(title) || blank(bodyText)) throw new IllegalArgumentException("required knowledge field missing");
            if (accessScope == AccessScope.PRIVATE && blank(ownerSubjectId))
                throw new IllegalArgumentException("private knowledge requires owner subject");
            if (bodyText.length() > 2_000_000) throw new IllegalArgumentException("document too large");
        }
        public IngestionRequest {
            language = blank(language) ? "ko" : language;
            metadataJson = blank(metadataJson) ? "{}" : metadataJson;
        }
    }
    public record IngestionResult(String documentId, int chunkCount, boolean duplicate) {}
    public record SearchRequest(String serviceId, String subjectId, String query, int limit) {
        void validate() {
            if (blank(serviceId) || blank(query) || limit < 1 || limit > 20)
                throw new IllegalArgumentException("invalid knowledge search");
        }
    }
    public record SearchResult(String chunkId, String documentId, String sourceId, String title, String content,
            double score, double lexicalScore, double semanticScore) {}
    private record Candidate(String id, String documentId, String sourceId, String title, String content,
            String embeddingModel, String embeddingJson) {}
    private static boolean blank(String value) { return value == null || value.isBlank(); }
}
