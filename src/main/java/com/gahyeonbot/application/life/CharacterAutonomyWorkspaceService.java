package com.gahyeonbot.application.life;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
public class CharacterAutonomyWorkspaceService {
    private final JdbcTemplate jdbc;

    public CharacterAutonomyWorkspaceService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Transactional
    public SoulRevision createSoulRevision(String characterId, String soulMarkdown, String createdBySubjectId) {
        require(characterId, "characterId");
        require(soulMarkdown, "soulMarkdown");
        require(createdBySubjectId, "createdBySubjectId");
        Long next = jdbc.queryForObject("""
                select coalesce(max(revision), 0) + 1 from character_identity_revisions where character_id = ?
                """, Long.class, characterId);
        String id = UUID.randomUUID().toString();
        jdbc.update("""
                insert into character_identity_revisions
                (id, character_id, revision, soul_markdown, created_by_subject_id, created_at)
                values (?, ?, ?, ?, ?, current_timestamp)
                """, id, characterId, next, soulMarkdown, createdBySubjectId);
        return new SoulRevision(id, characterId, next == null ? 1 : next, soulMarkdown, false);
    }

    @Transactional
    public void activateSoulRevision(String characterId, long revision) {
        jdbc.update("""
                update character_identity_revisions set retired_at = current_timestamp
                where character_id = ? and activated_at is not null and retired_at is null
                """, characterId);
        int changed = jdbc.update("""
                update character_identity_revisions set activated_at = current_timestamp, retired_at = null
                where character_id = ? and revision = ?
                """, characterId, revision);
        if (changed != 1) throw new NoSuchElementException("soul revision not found");
    }

    public Optional<SoulRevision> activeSoul(String characterId) {
        return jdbc.query("""
                select id, character_id, revision, soul_markdown from character_identity_revisions
                where character_id = ? and activated_at is not null and retired_at is null
                order by revision desc fetch first 1 row only
                """, rs -> rs.next() ? Optional.of(new SoulRevision(rs.getString(1), rs.getString(2),
                        rs.getLong(3), rs.getString(4), true)) : Optional.empty(), characterId);
    }

    public Todo addTodo(String characterId, String worldId, String ownerSubjectId, String description) {
        require(characterId, "characterId"); require(worldId, "worldId"); require(description, "description");
        String id = UUID.randomUUID().toString();
        jdbc.update("""
                insert into character_autonomy_todos
                (id, character_id, world_id, owner_subject_id, description, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, 'PENDING', current_timestamp, current_timestamp)
                """, id, characterId, worldId, ownerSubjectId, description);
        return new Todo(id, characterId, worldId, ownerSubjectId, description, "PENDING");
    }

    @Transactional
    public Optional<Todo> claimDueTodo(String characterId, String worldId) {
        Todo candidate = jdbc.query("""
                select id, character_id, world_id, owner_subject_id, description, status
                from character_autonomy_todos
                where character_id = ? and world_id = ? and status = 'PENDING'
                  and (not_before is null or not_before <= current_timestamp)
                order by created_at fetch first 1 row only
                """, rs -> rs.next() ? todo(rs) : null, characterId, worldId);
        if (candidate == null) return Optional.empty();
        int changed = jdbc.update("""
                update character_autonomy_todos set status = 'RUNNING', updated_at = current_timestamp
                where id = ? and status = 'PENDING'
                """, candidate.id());
        return changed == 1 ? Optional.of(new Todo(candidate.id(), candidate.characterId(), candidate.worldId(),
                candidate.ownerSubjectId(), candidate.description(), "RUNNING")) : Optional.empty();
    }

    public void completeTodo(String todoId, boolean success) {
        int changed = jdbc.update("""
                update character_autonomy_todos set status = ?, updated_at = current_timestamp
                where id = ? and status = 'RUNNING'
                """, success ? "COMPLETED" : "BLOCKED", todoId);
        if (changed != 1) throw new IllegalStateException("todo is not running");
    }

    @Transactional
    public GraphNode upsertGraphNode(String characterId, String worldId, String subjectId,
            String nodeType, String nodeKey, String label, String propertiesJson) {
        require(characterId, "characterId"); require(worldId, "worldId"); require(subjectId, "subjectId");
        require(nodeType, "nodeType"); require(nodeKey, "nodeKey"); require(label, "label");
        String existing = jdbc.query("""
                select id from memory_graph_nodes where character_id = ? and world_id = ?
                  and owner_subject_id = ? and node_type = ? and node_key = ?
                """, rs -> rs.next() ? rs.getString(1) : null,
                characterId, worldId, subjectId, nodeType, nodeKey);
        String id = existing == null ? UUID.randomUUID().toString() : existing;
        if (existing == null) {
            jdbc.update("""
                    insert into memory_graph_nodes
                    (id, character_id, world_id, owner_subject_id, node_type, node_key, label, properties_json,
                     created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp, current_timestamp)
                    """, id, characterId, worldId, subjectId, nodeType, nodeKey, label,
                    blank(propertiesJson) ? "{}" : propertiesJson);
        } else {
            jdbc.update("""
                    update memory_graph_nodes set label = ?, properties_json = ?, updated_at = current_timestamp
                    where id = ? and owner_subject_id = ?
                    """, label, blank(propertiesJson) ? "{}" : propertiesJson, id, subjectId);
        }
        return new GraphNode(id, characterId, worldId, subjectId, nodeType, nodeKey, label);
    }

    public GraphEdge connectGraphNodes(String characterId, String worldId, String subjectId,
            String fromNodeId, String toNodeId, String relationType, double weight, Long evidenceMemoryId) {
        if (weight < 0 || weight > 1) throw new IllegalArgumentException("weight must be between 0 and 1");
        Integer authorized = jdbc.queryForObject("""
                select count(*) from memory_graph_nodes where id in (?, ?) and character_id = ?
                  and world_id = ? and owner_subject_id = ?
                """, Integer.class, fromNodeId, toNodeId, characterId, worldId, subjectId);
        if (authorized == null || authorized != (fromNodeId.equals(toNodeId) ? 1 : 2))
            throw new IllegalArgumentException("graph nodes are outside authorized subject scope");
        String id = UUID.randomUUID().toString();
        jdbc.update("""
                insert into memory_graph_edges
                (id, character_id, world_id, owner_subject_id, from_node_id, to_node_id, relation_type,
                 weight, evidence_memory_id, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp, current_timestamp)
                """, id, characterId, worldId, subjectId, fromNodeId, toNodeId, relationType, weight, evidenceMemoryId);
        return new GraphEdge(id, fromNodeId, toNodeId, relationType, weight);
    }

    private static Todo todo(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new Todo(rs.getString(1), rs.getString(2), rs.getString(3), rs.getString(4),
                rs.getString(5), rs.getString(6));
    }
    private static void require(String value, String name) {
        if (blank(value)) throw new IllegalArgumentException(name + " is required");
    }
    private static boolean blank(String value) { return value == null || value.isBlank(); }

    public record SoulRevision(String id, String characterId, long revision, String soulMarkdown, boolean active) {}
    public record Todo(String id, String characterId, String worldId, String ownerSubjectId,
            String description, String status) {}
    public record GraphNode(String id, String characterId, String worldId, String ownerSubjectId,
            String nodeType, String nodeKey, String label) {}
    public record GraphEdge(String id, String fromNodeId, String toNodeId, String relationType, double weight) {}
}
