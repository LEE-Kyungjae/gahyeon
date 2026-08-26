package com.gahyeonbot.application.knowledge;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class KnowledgeBaseServiceTest {
    private KnowledgeBaseService service;

    @BeforeEach
    void setUp() {
        var dataSource = new DriverManagerDataSource("jdbc:h2:mem:knowledge;MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
        var jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("drop all objects");
        jdbc.execute("""
                create table knowledge_sources (
                  id varchar(36) primary key, service_id varchar(64) not null, owner_subject_id varchar(160),
                  source_type varchar(32) not null, display_name varchar(240) not null, source_uri varchar(2048),
                  access_scope varchar(24) not null, lifecycle_status varchar(24) not null,
                  content_sha256 varchar(64), created_at timestamp with time zone not null,
                  updated_at timestamp with time zone not null, deleted_at timestamp with time zone)
                """);
        jdbc.execute("""
                create table knowledge_documents (
                  id varchar(36) primary key, source_id varchar(36) not null, service_id varchar(64) not null,
                  owner_subject_id varchar(160), title varchar(500) not null, language varchar(16) not null,
                  body_text clob not null, metadata_json clob not null, content_sha256 varchar(64) not null,
                  version bigint not null, created_at timestamp with time zone not null,
                  updated_at timestamp with time zone not null, deleted_at timestamp with time zone)
                """);
        jdbc.execute("""
                create table knowledge_chunks (
                  id varchar(36) primary key, document_id varchar(36) not null, source_id varchar(36) not null,
                  service_id varchar(64) not null, owner_subject_id varchar(160), ordinal integer not null,
                  content clob not null, token_count integer not null, embedding_model varchar(160),
                  embedding_json clob, created_at timestamp with time zone not null,
                  deleted_at timestamp with time zone)
                """);
        @SuppressWarnings("unchecked") ObjectProvider<KnowledgeEmbeddingPort> embeddings = mock(ObjectProvider.class);
        service = new KnowledgeBaseService(jdbc, embeddings, new ObjectMapper(),
                Clock.fixed(Instant.parse("2026-08-26T00:00:00Z"), ZoneOffset.UTC));
    }

    @Test
    void runtimeConstructorIsExplicitForSpring() {
        assertThat(java.util.Arrays.stream(KnowledgeBaseService.class.getDeclaredConstructors())
                .filter(constructor -> constructor.isAnnotationPresent(Autowired.class)))
                .hasSize(1);
    }

    @Test
    void privateKnowledgeIsRetrievedOnlyForItsExactOwnerAndService() {
        service.ingest(request("gahyeon", "zezestudio:user-a", KnowledgeBaseService.AccessScope.PRIVATE,
                "사용자는 민트초코를 좋아한다."));
        service.ingest(request("gahyeon", "zezestudio:user-b", KnowledgeBaseService.AccessScope.PRIVATE,
                "사용자는 민트초코를 싫어한다."));

        assertThat(service.search(new KnowledgeBaseService.SearchRequest(
                "gahyeon", "zezestudio:user-a", "민트초코 좋아한다", 10)))
                .extracting(KnowledgeBaseService.SearchResult::content)
                .containsExactly("사용자는 민트초코를 좋아한다.");
        assertThat(service.search(new KnowledgeBaseService.SearchRequest(
                "other-service", "zezestudio:user-a", "민트초코", 10))).isEmpty();
    }

    @Test
    void ingestionIsIdempotentAndSourceDeletionRemovesAllChunksFromRecall() {
        var first = service.ingest(request("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE,
                "가현 서비스 운영 지식"));
        var duplicate = service.ingest(request("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE,
                "가현 서비스 운영 지식"));

        assertThat(duplicate.duplicate()).isTrue();
        assertThat(duplicate.documentId()).isEqualTo(first.documentId());
        var found = service.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "운영 지식", 10));
        assertThat(found).hasSize(1);

        service.softDeleteSource("gahyeon", null, found.getFirst().sourceId());
        assertThat(service.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "운영 지식", 10)))
                .isEmpty();
    }

    @Test
    void ranksACompleteKoreanPhraseAboveARecentSingleTermDistractor() {
        service.ingest(request("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE,
                "프로젝트에 관한 일반적인 회의 기록이다."));
        service.ingest(new KnowledgeBaseService.IngestionRequest(
                "gahyeon", null, "text", "release-plan", null,
                KnowledgeBaseService.AccessScope.SERVICE, "가현 프로젝트 배포 일정", "ko",
                "가현 프로젝트 배포 일정은 금요일 오후 세 시다.", "{}"));

        assertThat(service.search(new KnowledgeBaseService.SearchRequest(
                "gahyeon", null, "가현 프로젝트 배포 일정", 10)))
                .extracting(KnowledgeBaseService.SearchResult::title)
                .startsWith("가현 프로젝트 배포 일정", "테스트 문서");
    }

    private static KnowledgeBaseService.IngestionRequest request(String serviceId, String owner,
            KnowledgeBaseService.AccessScope scope, String body) {
        return new KnowledgeBaseService.IngestionRequest(serviceId, owner, "text", "test", null, scope,
                "테스트 문서", "ko", body, "{}");
    }
}
