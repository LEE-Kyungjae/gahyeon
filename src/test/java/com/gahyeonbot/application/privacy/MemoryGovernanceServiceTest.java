package com.gahyeonbot.application.privacy;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class MemoryGovernanceServiceTest {
    private JdbcTemplate jdbc;
    private MemoryGovernanceService service;
    private RecordingDeletionPort vector;
    private RecordingDeletionPort cache;

    @BeforeEach
    void setUp() {
        var dataSource = new DriverManagerDataSource("jdbc:h2:mem:governance;MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
        jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("drop all objects");
        jdbc.execute("create table external_identities (principal_id bigint, provider varchar(30), external_id varchar(200))");
        jdbc.execute("""
                create table memory_identity_merge_requests (
                  id varchar(36) primary key, principal_id bigint, source_subject_id varchar(160),
                  target_subject_id varchar(160), status varchar(24), approval_digest varchar(64),
                  requested_at timestamp with time zone, decided_at timestamp with time zone,
                  completed_at timestamp with time zone, failure_class varchar(120))
                """);
        jdbc.execute("create table character_memories (id bigint primary key, subject_id varchar(160))");
        jdbc.execute("""
                create table character_relationship_states (
                  character_id varchar(64), world_id varchar(100), subject_id varchar(160), storage_version bigint,
                  revision bigint, familiarity double, trust double, affinity double, tension double,
                  updated_at timestamp with time zone, primary key(character_id, world_id, subject_id))
                """);
        jdbc.execute("create table knowledge_chunks (service_id varchar(64), owner_subject_id varchar(160))");
        jdbc.execute("create table knowledge_documents (service_id varchar(64), owner_subject_id varchar(160))");
        jdbc.execute("create table knowledge_sources (service_id varchar(64), owner_subject_id varchar(160))");
        jdbc.execute("create table conversation_history (user_id bigint)");
        jdbc.execute("""
                create table privacy_deletion_jobs (
                  id varchar(36), service_id varchar(64), subject_id varchar(160), status varchar(24),
                  postgres_deleted boolean default false, vector_deleted boolean default false,
                  cache_deleted boolean default false, derived_deleted boolean default false,
                  requested_at timestamp with time zone, completed_at timestamp with time zone, failure_class varchar(120))
                """);
        vector = new RecordingDeletionPort(SubjectDataDeletionPort.Layer.VECTOR);
        cache = new RecordingDeletionPort(SubjectDataDeletionPort.Layer.CACHE);
        @SuppressWarnings("unchecked") ObjectProvider<SubjectDataDeletionPort> ports = mock(ObjectProvider.class);
        when(ports.orderedStream()).thenReturn(Stream.of(vector, cache));
        service = new MemoryGovernanceService(jdbc, ports, new DataSourceTransactionManager(dataSource));
        jdbc.update("insert into external_identities values (42, 'ZEZESTUDIO', ?)",
                "11111111-1111-1111-1111-111111111111");
    }

    @Test
    void preLinkMemoryMovesOnlyAfterExplicitApproval() {
        jdbc.update("insert into character_memories values (1, 'principal:42')");
        jdbc.update("""
                insert into character_relationship_states values
                ('gahyeon', 'home', 'principal:42', 0, 2, .5, .6, .7, .1, current_timestamp)
                """);
        var request = service.requestMerge(42, "principal:42",
                "zezestudio:11111111-1111-1111-1111-111111111111");

        assertThatThrownBy(() -> service.executeApprovedMerge(request.id()))
                .isInstanceOf(IllegalStateException.class);
        assertThat(jdbc.queryForObject("select subject_id from character_memories where id = 1", String.class))
                .isEqualTo("principal:42");

        service.approveMerge(request.id(), "user-confirmed-proof-2026-08-26");
        var result = service.executeApprovedMerge(request.id());

        assertThat(result.memoriesMoved()).isEqualTo(1);
        assertThat(result.relationshipsMerged()).isEqualTo(1);
        assertThat(jdbc.queryForObject("select subject_id from character_memories where id = 1", String.class))
                .isEqualTo("zezestudio:11111111-1111-1111-1111-111111111111");
    }

    @Test
    void deletionPropagatesAcrossPostgresVectorCacheAndDerivedMemory() {
        String subject = "zezestudio:11111111-1111-1111-1111-111111111111";
        jdbc.update("insert into character_memories values (1, ?)", subject);
        jdbc.update("insert into knowledge_chunks values ('gahyeon', ?)", subject);
        jdbc.update("insert into knowledge_documents values ('gahyeon', ?)", subject);
        jdbc.update("insert into knowledge_sources values ('gahyeon', ?)", subject);
        jdbc.update("insert into conversation_history values (42)");

        var result = service.deleteSubject(42, "gahyeon", subject);

        assertThat(result.postgresRowsDeleted()).isEqualTo(5);
        assertThat(result.vectorDeleted()).isTrue();
        assertThat(result.cacheDeleted()).isTrue();
        assertThat(result.derivedDeleted()).isTrue();
        assertThat(vector.lastSubject).isEqualTo(subject);
        assertThat(cache.lastSubject).isEqualTo(subject);
        assertThat(jdbc.queryForObject("select status from privacy_deletion_jobs where id = ?",
                String.class, result.jobId())).isEqualTo("COMPLETED");
    }

    private static final class RecordingDeletionPort implements SubjectDataDeletionPort {
        private final Layer layer;
        private String lastSubject;
        private RecordingDeletionPort(Layer layer) { this.layer = layer; }
        public Layer layer() { return layer; }
        public void delete(String serviceId, String subjectId) { lastSubject = subjectId; }
    }
}
