package com.gahyeonbot.application.privacy;

import com.gahyeonbot.core.identity.IdentityProvider;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class MemoryGovernanceService {
    private final JdbcTemplate jdbc;
    private final List<SubjectDataDeletionPort> externalDeletion;
    private final TransactionTemplate transactions;

    public MemoryGovernanceService(JdbcTemplate jdbc, ObjectProvider<SubjectDataDeletionPort> externalDeletion,
            PlatformTransactionManager transactionManager) {
        this.jdbc = jdbc;
        this.externalDeletion = externalDeletion.orderedStream().toList();
        this.transactions = new TransactionTemplate(transactionManager);
    }

    public MergeRequest requestMerge(long principalId, String sourceSubjectId, String targetSubjectId) {
        requireMergeNamespaces(principalId, sourceSubjectId, targetSubjectId);
        String linked = jdbc.query("""
                select external_id from external_identities
                where principal_id = ? and provider = ? and external_id = ? fetch first 1 row only
                """, rs -> rs.next() ? rs.getString(1) : null,
                principalId, IdentityProvider.ZEZESTUDIO.name(), targetSubjectId.substring("zezestudio:".length()));
        if (linked == null) throw new IllegalArgumentException("target ZezeStudio identity is not linked to principal");
        String id = UUID.randomUUID().toString();
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        jdbc.update("""
                insert into memory_identity_merge_requests
                (id, principal_id, source_subject_id, target_subject_id, status, requested_at)
                values (?, ?, ?, ?, 'PENDING', ?)
                """, id, principalId, sourceSubjectId, targetSubjectId, now);
        return new MergeRequest(id, principalId, sourceSubjectId, targetSubjectId, "PENDING");
    }

    public void approveMerge(String requestId, String userApprovalProof) {
        if (userApprovalProof == null || userApprovalProof.length() < 16)
            throw new IllegalArgumentException("explicit user approval proof is required");
        int changed = jdbc.update("""
                update memory_identity_merge_requests
                set status = 'APPROVED', approval_digest = ?, decided_at = current_timestamp
                where id = ? and status = 'PENDING'
                """, sha256(userApprovalProof), requestId);
        if (changed != 1) throw new IllegalStateException("merge request is not pending");
    }

    public MergeResult executeApprovedMerge(String requestId) {
        MergeRow row = jdbc.query("""
                select principal_id, source_subject_id, target_subject_id, status
                from memory_identity_merge_requests where id = ?
                """, rs -> rs.next() ? new MergeRow(rs.getLong(1), rs.getString(2), rs.getString(3), rs.getString(4)) : null,
                requestId);
        if (row == null || !"APPROVED".equals(row.status()))
            throw new IllegalStateException("explicitly approved merge request required");
        return Objects.requireNonNull(transactions.execute(status -> {
            int memories = jdbc.update("update character_memories set subject_id = ? where subject_id = ?",
                    row.target(), row.source());
            int relationships = mergeRelationships(row.source(), row.target());
            jdbc.update("""
                    update memory_identity_merge_requests set status = 'COMPLETED', completed_at = current_timestamp
                    where id = ? and status = 'APPROVED'
                    """, requestId);
            return new MergeResult(memories, relationships);
        }));
    }

    public DeletionResult deleteSubject(long principalId, String serviceId, String subjectId) {
        if (serviceId == null || serviceId.isBlank() || subjectId == null || subjectId.isBlank())
            throw new IllegalArgumentException("service and subject are required");
        authorizeSubject(principalId, subjectId);
        String jobId = UUID.randomUUID().toString();
        jdbc.update("""
                insert into privacy_deletion_jobs
                (id, service_id, subject_id, status, requested_at) values (?, ?, ?, 'RUNNING', current_timestamp)
                """, jobId, serviceId, subjectId);
        int postgresDeleted;
        try {
            postgresDeleted = Objects.requireNonNull(transactions.execute(status -> deletePostgres(serviceId, subjectId, principalId)));
            jdbc.update("update privacy_deletion_jobs set postgres_deleted = true, derived_deleted = true where id = ?", jobId);
            EnumSet<SubjectDataDeletionPort.Layer> completed = EnumSet.noneOf(SubjectDataDeletionPort.Layer.class);
            for (SubjectDataDeletionPort port : externalDeletion) {
                port.delete(serviceId, subjectId);
                completed.add(port.layer());
            }
            boolean vector = completed.contains(SubjectDataDeletionPort.Layer.VECTOR)
                    || externalDeletion.stream().noneMatch(port -> port.layer() == SubjectDataDeletionPort.Layer.VECTOR);
            boolean cache = completed.contains(SubjectDataDeletionPort.Layer.CACHE)
                    || externalDeletion.stream().noneMatch(port -> port.layer() == SubjectDataDeletionPort.Layer.CACHE);
            jdbc.update("""
                    update privacy_deletion_jobs set vector_deleted = ?, cache_deleted = ?, status = 'COMPLETED',
                        completed_at = current_timestamp where id = ?
                    """, vector, cache, jobId);
            return new DeletionResult(jobId, postgresDeleted, vector, cache, true);
        } catch (RuntimeException failure) {
            jdbc.update("update privacy_deletion_jobs set status = 'FAILED', failure_class = ? where id = ?",
                    failure.getClass().getSimpleName(), jobId);
            throw failure;
        }
    }

    private int deletePostgres(String serviceId, String subjectId, long principalId) {
        int deleted = jdbc.update("delete from character_memories where subject_id = ?", subjectId);
        deleted += jdbc.update("delete from character_relationship_states where subject_id = ?", subjectId);
        deleted += jdbc.update("delete from knowledge_chunks where service_id = ? and owner_subject_id = ?", serviceId, subjectId);
        deleted += jdbc.update("delete from knowledge_documents where service_id = ? and owner_subject_id = ?", serviceId, subjectId);
        deleted += jdbc.update("delete from knowledge_sources where service_id = ? and owner_subject_id = ?", serviceId, subjectId);
        deleted += jdbc.update("delete from conversation_history where user_id = ?", principalId);
        return deleted;
    }

    private int mergeRelationships(String source, String target) {
        List<RelationshipRow> rows = jdbc.query("""
                select character_id, world_id, storage_version, revision, familiarity, trust, affinity, tension
                from character_relationship_states where subject_id = ?
                """, (rs, row) -> new RelationshipRow(rs.getString(1), rs.getString(2), rs.getLong(3),
                        rs.getLong(4), rs.getDouble(5), rs.getDouble(6), rs.getDouble(7), rs.getDouble(8)), source);
        for (RelationshipRow row : rows) {
            Integer targetExists = jdbc.queryForObject("""
                    select count(*) from character_relationship_states
                    where character_id = ? and world_id = ? and subject_id = ?
                    """, Integer.class, row.characterId(), row.worldId(), target);
            if (targetExists != null && targetExists > 0) {
                jdbc.update("""
                        update character_relationship_states set
                          revision = greatest(revision, ?), familiarity = greatest(familiarity, ?),
                          trust = greatest(trust, ?), affinity = greatest(affinity, ?), tension = greatest(tension, ?),
                          updated_at = current_timestamp
                        where character_id = ? and world_id = ? and subject_id = ?
                        """, row.revision(), row.familiarity(), row.trust(), row.affinity(), row.tension(),
                        row.characterId(), row.worldId(), target);
                jdbc.update("""
                        delete from character_relationship_states
                        where character_id = ? and world_id = ? and subject_id = ?
                        """, row.characterId(), row.worldId(), source);
            } else {
                jdbc.update("""
                        update character_relationship_states set subject_id = ?, updated_at = current_timestamp
                        where character_id = ? and world_id = ? and subject_id = ?
                        """, target, row.characterId(), row.worldId(), source);
            }
        }
        return rows.size();
    }

    private void authorizeSubject(long principalId, String subjectId) {
        if (subjectId.equals("principal:" + principalId)) return;
        if (!subjectId.startsWith("zezestudio:")) throw new IllegalArgumentException("subject is not owned by principal");
        int count = Optional.ofNullable(jdbc.queryForObject("""
                select count(*) from external_identities where principal_id = ? and provider = ? and external_id = ?
                """, Integer.class, principalId, IdentityProvider.ZEZESTUDIO.name(),
                subjectId.substring("zezestudio:".length()))).orElse(0);
        if (count != 1) throw new IllegalArgumentException("subject is not owned by principal");
    }

    private static void requireMergeNamespaces(long principalId, String source, String target) {
        if (!Objects.equals(source, "principal:" + principalId) || target == null || !target.startsWith("zezestudio:"))
            throw new IllegalArgumentException("only own provisional-to-ZezeStudio merge is allowed");
        UUID.fromString(target.substring("zezestudio:".length()));
    }

    private static String sha256(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception impossible) { throw new IllegalStateException(impossible); }
    }

    public record MergeRequest(String id, long principalId, String sourceSubjectId, String targetSubjectId, String status) {}
    public record MergeResult(int memoriesMoved, int relationshipsMerged) {}
    public record DeletionResult(String jobId, int postgresRowsDeleted, boolean vectorDeleted,
            boolean cacheDeleted, boolean derivedDeleted) {}
    private record MergeRow(long principalId, String source, String target, String status) {}
    private record RelationshipRow(String characterId, String worldId, long storageVersion, long revision,
            double familiarity, double trust, double affinity, double tension) {}
}
