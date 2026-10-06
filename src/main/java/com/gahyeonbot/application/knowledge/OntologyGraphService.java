package com.gahyeonbot.application.knowledge;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

@Service
public class OntologyGraphService {
    private static final int MAX_CLAIMS = 2000;
    private static final int MAX_SEEDS = 8;
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public OntologyGraphService(JdbcTemplate jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    /** Replace one document's claims atomically, with its row locked to serialize reindexing. */
    @Transactional
    public int index(String serviceId, String owner, String documentId, OntologySchema.Document ontology) {
        Objects.requireNonNull(ontology);
        List<String> authorized = jdbc.query("""
                select d.id from knowledge_documents d join knowledge_sources s on s.id = d.source_id
                where d.id = ? and d.service_id = ? and s.service_id = ?
                  and ((s.owner_subject_id is null and cast(? as varchar) is null) or s.owner_subject_id = ?)
                  and ((d.owner_subject_id is null and cast(? as varchar) is null) or d.owner_subject_id = ?)
                  and d.deleted_at is null and s.deleted_at is null and s.lifecycle_status = 'ACTIVE'
                for update
                """, (rs, row) -> rs.getString(1), documentId, serviceId, serviceId, owner, owner, owner, owner);
        if (authorized.size() != 1) throw new NoSuchElementException("Authorized active document not found");
        var chunks = jdbc.query("""
                select id, content from knowledge_chunks where document_id = ? and service_id = ?
                  and ((owner_subject_id is null and cast(? as varchar) is null) or owner_subject_id = ?)
                  and deleted_at is null order by ordinal
                """, (rs, row) -> new Chunk(rs.getString(1), rs.getString(2)), documentId, serviceId, owner, owner);
        Map<String, IndexedClaim> validated = new LinkedHashMap<>();
        for (var claim : ontology.claims()) {
            Chunk evidence = chunks.stream().filter(chunk -> chunk.content().contains(claim.evidenceQuote()))
                    .findFirst().orElseThrow(() -> new IllegalArgumentException("Claim quote must occur verbatim in one source chunk"));
            // Labels must be grounded too; aliases are reviewed mappings, not evidence of the predicate.
            if (!claim.subject().names().stream().anyMatch(claim.evidenceQuote()::contains)
                    || !claim.object().names().stream().anyMatch(claim.evidenceQuote()::contains))
                throw new IllegalArgumentException("Evidence must mention both entities");
            String id = digest(documentId + "\n" + claim.subject().identity() + "\n" + claim.relation()
                    + "\n" + claim.object().identity() + "\n" + claim.evidenceQuote());
            validated.putIfAbsent(id, new IndexedClaim(id, evidence.id(), claim));
        }
        jdbc.update("delete from knowledge_ontology_claims where chunk_id in (select id from knowledge_chunks where document_id = ?)", documentId);
        for (var indexed : validated.values()) {
            var claim = indexed.claim();
            jdbc.update("""
                    insert into knowledge_ontology_claims
                    (id, chunk_id, schema_version, subject_key, subject_type, subject_label, subject_aliases,
                     relation_type, object_key, object_type, object_label, object_aliases, evidence_quote)
                    values (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, indexed.id(), indexed.chunkId(), claim.subject().key(), claim.subject().type().name(),
                    claim.subject().label(), encode(claim.subject().aliases()), claim.relation().name(),
                    claim.object().key(), claim.object().type().name(), claim.object().label(),
                    encode(claim.object().aliases()), claim.evidenceQuote());
        }
        return validated.size();
    }

    public SearchReport search(Query query) {
        // No private names, aliases or edges enter memory before source-level authorization.
        List<Edge> loaded = jdbc.query("""
                select o.*, c.document_id, c.source_id, d.title, c.content
                from knowledge_ontology_claims o
                join knowledge_chunks c on c.id = o.chunk_id
                join knowledge_documents d on d.id = c.document_id and d.source_id = c.source_id
                join knowledge_sources s on s.id = c.source_id
                where c.service_id = ? and d.service_id = ? and s.service_id = ?
                  and c.deleted_at is null and d.deleted_at is null and s.deleted_at is null
                  and s.lifecycle_status = 'ACTIVE' and o.schema_version = 1
                  and (s.access_scope in ('PUBLIC', 'SERVICE') or
                       (s.access_scope = 'PRIVATE' and s.owner_subject_id = ?
                        and d.owner_subject_id = ? and c.owner_subject_id = ?))
                order by o.id fetch first 2001 rows only
                """, (rs, row) -> new Edge(rs.getString("id"), rs.getString("chunk_id"),
                        rs.getString("document_id"), rs.getString("source_id"), rs.getString("title"),
                        rs.getString("content"),
                        new OntologySchema.Claim(
                                new OntologySchema.Entity(rs.getString("subject_key"), OntologySchema.Type.valueOf(rs.getString("subject_type")),
                                        rs.getString("subject_label"), decode(rs.getString("subject_aliases"))),
                                OntologySchema.Relation.valueOf(rs.getString("relation_type")),
                                new OntologySchema.Entity(rs.getString("object_key"), OntologySchema.Type.valueOf(rs.getString("object_type")),
                                        rs.getString("object_label"), decode(rs.getString("object_aliases"))), rs.getString("evidence_quote"))),
                query.serviceId(), query.serviceId(), query.serviceId(), query.subjectId(), query.subjectId(), query.subjectId());
        boolean truncated = loaded.size() > MAX_CLAIMS;
        List<Edge> edges = loaded.stream().limit(MAX_CLAIMS).toList();
        Map<String, List<Edge>> adjacent = new LinkedHashMap<>();
        Map<String, Integer> seedMatches = new HashMap<>();
        String normalized = normalize(query.query());
        for (Edge edge : edges) for (var entity : List.of(edge.claim().subject(), edge.claim().object())) {
            adjacent.computeIfAbsent(entity.identity(), ignored -> new ArrayList<>()).add(edge);
            int match = entity.names().stream().map(OntologyGraphService::normalize)
                    .filter(name -> matches(normalized, name)).mapToInt(String::length).max().orElse(0);
            if (match > 0) seedMatches.merge(entity.identity(), match, Math::max);
        }
        List<String> seeds = seedMatches.keySet().stream().sorted(
                Comparator.<String>comparingInt(seedMatches::get).reversed().thenComparing(key -> key)).limit(MAX_SEEDS).toList();
        truncated |= seedMatches.size() > MAX_SEEDS;
        Map<String, EvidencePath> found = new LinkedHashMap<>();
        for (String seed : seeds) {
            ArrayDeque<Visit> queue = new ArrayDeque<>();
            Set<String> visited = new HashSet<>();
            queue.add(new Visit(seed, List.of()));
            visited.add(seed);
            while (!queue.isEmpty()) {
                Visit visit = queue.removeFirst();
                if (visit.path().size() >= query.maxHops()) continue;
                for (Edge edge : adjacent.getOrDefault(visit.entity(), List.of())) {
                    if (visit.path().stream().anyMatch(prior -> prior.id().equals(edge.id()))) continue;
                    List<Edge> path = new ArrayList<>(visit.path()); path.add(edge);
                    EvidencePath candidate = new EvidencePath(seed, List.copyOf(path));
                    var previous = found.get(edge.id());
                    if (previous == null || previous.edges().size() > path.size()) found.put(edge.id(), candidate);
                    String next = edge.claim().subject().identity().equals(visit.entity())
                            ? edge.claim().object().identity() : edge.claim().subject().identity();
                    if (visited.add(next)) queue.addLast(new Visit(next, List.copyOf(path)));
                }
            }
        }
        List<EvidencePath> ranked = found.values().stream().sorted(Comparator
                .comparingInt((EvidencePath path) -> path.edges().size())
                .thenComparing(path -> path.edges().getLast().id())).toList();
        return new SearchReport(ranked.stream().limit(query.limit()).toList(),
                truncated || ranked.size() > query.limit(), edges.size());
    }

    private static boolean matches(String query, String name) {
        if (name.length() < 2) return false;
        if (name.matches("[a-z0-9 ]+"))
            return java.util.regex.Pattern.compile("(?<![a-z0-9])" + java.util.regex.Pattern.quote(name)
                    + "(?![a-z0-9])").matcher(query).find();
        return query.contains(name);
    }
    private static String normalize(String value) {
        return java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFKC)
                .toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]+", " ").strip();
    }
    private String encode(List<String> aliases) {
        try { return json.writeValueAsString(aliases); }
        catch (Exception failure) { throw new IllegalArgumentException("Invalid ontology aliases", failure); }
    }
    private List<String> decode(String value) {
        try { return json.readValue(value, new TypeReference<>() {}); }
        catch (Exception failure) { throw new IllegalStateException("Invalid persisted ontology aliases", failure); }
    }
    private static String digest(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (Exception failure) { throw new IllegalStateException(failure); }
    }
    public record Query(String serviceId, String subjectId, String query, int limit, int maxHops) {
        public Query {
            if (serviceId == null || serviceId.isBlank() || query == null || query.isBlank() || query.length() > 2000
                    || limit < 1 || limit > 20 || maxHops < 1 || maxHops > 3)
                throw new IllegalArgumentException("Invalid ontology query");
        }
    }
    public record Edge(String id, String chunkId, String documentId, String sourceId, String title,
            String content, OntologySchema.Claim claim) {}
    public record EvidencePath(String seed, List<Edge> edges) {}
    public record SearchReport(List<EvidencePath> paths, boolean truncated, int authorizedClaimsScanned) {}
    private record Chunk(String id, String content) {}
    private record IndexedClaim(String id, String chunkId, OntologySchema.Claim claim) {}
    private record Visit(String entity, List<Edge> path) {}
}
