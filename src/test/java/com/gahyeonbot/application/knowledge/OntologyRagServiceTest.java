package com.gahyeonbot.application.knowledge;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.*;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.*;

import static com.gahyeonbot.application.knowledge.OntologySchema.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@SpringJUnitConfig(OntologyRagServiceTest.Config.class)
class OntologyRagServiceTest {
    @Autowired JdbcTemplate jdbc;
    @Autowired KnowledgeBaseService knowledge;
    @Autowired OntologyGraphService graph;
    @Autowired OntologyIngestionService ingestion;
    @Autowired OntologyRagService rag;

    @BeforeEach void reset() {
        jdbc.update("delete from knowledge_chunks");
        jdbc.update("delete from knowledge_documents");
        jdbc.update("delete from knowledge_sources");
    }

    @Test void aliasSeedFindsTwoHopRelationshipAndEverySourceCitation() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        addOwner("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        var report = graph.search(query("gahyeon", null, "새벽 담당자는 누구야", 2));
        assertThat(report.paths()).hasSize(2);
        var path = report.paths().stream().filter(p -> p.edges().size() == 2).findFirst().orElseThrow();
        assertThat(path.edges()).extracting(e -> e.claim().relation()).containsExactly(Relation.PART_OF, Relation.RESPONSIBLE_FOR);
        assertThat(path.edges()).extracting(OntologyGraphService.Edge::sourceId).doesNotHaveDuplicates();
        assertThat(knowledge.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "새벽", 10))).isEmpty();
        var result = rag.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "새벽", 10));
        assertThat(result.results()).anySatisfy(item -> assertThat(item.content())
                .contains("민지", "출시 검증", "PART_OF", "RESPONSIBLE_FOR", "source=", "원문:"));
    }

    @Test void privateEdgeCannotBridgeForAnotherUserOrAnonymous() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        addOwner("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PRIVATE);
        assertThat(graph.search(query("gahyeon", "user-a", "새벽", 2)).paths()).hasSize(2);
        for (String subject : Arrays.asList("user-b", null)) {
            var report = graph.search(query("gahyeon", subject, "새벽", 2));
            assertThat(report.paths()).hasSize(1);
            assertThat(report.toString()).doesNotContain("민지", "person:minji");
            assertThat(graph.search(query("gahyeon", subject, "민지", 2)).paths()).isEmpty();
        }
    }

    @Test void serviceBoundaryIsAppliedBeforeEntityMatchingAndTraversal() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        addOwner("other", null, KnowledgeBaseService.AccessScope.PUBLIC);
        assertThat(graph.search(query("gahyeon", null, "새벽", 2)).paths()).hasSize(1);
        assertThat(graph.search(query("other", null, "새벽", 2)).paths()).isEmpty();
    }

    @Test void softDeletedOrDisabledSourcesCannotSupplyEdges() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        var owner = addOwner("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        String source = jdbc.queryForObject("select source_id from knowledge_documents where id = ?", String.class, owner.documentId());
        jdbc.update("update knowledge_sources set lifecycle_status = 'DISABLED' where id = ?", source);
        assertThat(graph.search(query("gahyeon", null, "새벽", 2)).paths()).hasSize(1);
        jdbc.update("update knowledge_sources set lifecycle_status = 'ACTIVE' where id = ?", source);
        knowledge.softDeleteSource("gahyeon", null, source);
        assertThat(graph.search(query("gahyeon", null, "새벽", 2)).paths()).hasSize(1);
    }

    @Test void deletingSourceChunksRemovesDerivedPrivateClaimsByCascade() {
        addOwner("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PRIVATE);
        assertThat(jdbc.queryForObject("select count(*) from knowledge_ontology_claims", Integer.class)).isEqualTo(1);
        jdbc.update("delete from knowledge_chunks where owner_subject_id = ?", "user-a");
        assertThat(jdbc.queryForObject("select count(*) from knowledge_ontology_claims", Integer.class)).isZero();
    }

    @Test void invalidEvidenceRollsBackEntireDocumentIngestion() {
        var invalid = new Document(1, List.of(new Claim(person(), Relation.RESPONSIBLE_FOR, task(),
                "민지는 출시 검증을 맡는다는 내용은 이 원문에는 없다.")));
        assertThatThrownBy(() -> ingestion.ingest(document("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE,
                "민지는 출시 검증을 맡았다."), invalid)).hasMessageContaining("verbatim");
        assertThat(jdbc.queryForObject("select count(*) from knowledge_sources", Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from knowledge_chunks", Integer.class)).isZero();
    }

    @Test void reindexIsIdempotentAndInvalidReplacementPreservesExistingClaims() {
        var result = addOwner("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PRIVATE);
        addOwner("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PRIVATE);
        assertThat(jdbc.queryForObject("select count(*) from knowledge_ontology_claims", Integer.class)).isEqualTo(1);
        var invalid = new Document(1, List.of(new Claim(person(), Relation.RESPONSIBLE_FOR, task(), "민지는 출시 검증을 맡지 않았다.")));
        assertThatThrownBy(() -> graph.index("gahyeon", "user-a", result.documentId(), invalid))
                .hasMessageContaining("verbatim");
        assertThat(graph.search(query("gahyeon", "user-a", "민지", 1)).paths()).hasSize(1);
        assertThatThrownBy(() -> graph.index("gahyeon", "user-b", result.documentId(), ownerOntology()))
                .isInstanceOf(NoSuchElementException.class);
    }

    @Test void domainRangeAndUnsupportedSchemaAreRejected() {
        assertThatThrownBy(() -> new Claim(task(), Relation.MEMBER_OF, person(), "출시 검증은 민지 소속이다."))
                .hasMessageContaining("domain/range");
        assertThatThrownBy(() -> new Document(2, ownerOntology().claims())).hasMessageContaining("schema 1");
    }

    @Test void quoteMustNameBothEntitiesEvenWhenItExistsInSource() {
        var claim = new Claim(person(), Relation.RESPONSIBLE_FOR, task(), "이번 주에는 비가 내렸다.");
        assertThatThrownBy(() -> ingestion.ingest(document("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE,
                "이번 주에는 비가 내렸다."), new Document(1, List.of(claim)))).hasMessageContaining("both entities");
    }

    @Test void privateClaimsCannotAttachToLegacyPublicDuplicate() {
        knowledge.ingest(document("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PUBLIC, "민지는 출시 검증을 맡았다."));
        assertThatThrownBy(() -> addOwner("gahyeon", "user-a", KnowledgeBaseService.AccessScope.PRIVATE))
                .hasMessageContaining("different access scope");
        assertThat(jdbc.queryForObject("select count(*) from knowledge_ontology_claims", Integer.class)).isZero();
    }

    @Test void maxHopsAndUnknownEntitiesDoNotInventRelations() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        addOwner("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        assertThat(graph.search(query("gahyeon", null, "새벽", 1)).paths()).hasSize(1);
        assertThat(graph.search(query("gahyeon", null, "존재하지않는개체", 3)).paths()).isEmpty();
        assertThatThrownBy(() -> query("gahyeon", null, "새벽", 4)).hasMessageContaining("Invalid");
    }

    @Test void disabledRagNeverQueriesOntologyTables() {
        var mockedGraph = mock(OntologyGraphService.class);
        var disabled = new OntologyRagService(knowledge, mockedGraph, false);
        knowledge.ingest(document("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE, "오로라 자료입니다."));
        assertThat(disabled.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "오로라", 10)).results()).hasSize(1);
        verifyNoInteractions(mockedGraph);
    }

    @Test void actualPromptReceivesAuthorizedTwoHopEvidenceFromStoredDocuments() {
        addProject("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        addOwner("gahyeon", "actor:101", KnowledgeBaseService.AccessScope.PRIVATE);
        var provider = new com.gahyeonbot.services.ai.agent.AgentPromptProvider();
        org.springframework.test.util.ReflectionTestUtils.invokeMethod(provider, "load");
        org.springframework.test.util.ReflectionTestUtils.invokeMethod(provider, "configureCharacters",
                new com.gahyeonbot.application.life.CharacterDefinitionRegistry(
                        com.gahyeonbot.application.life.CharacterCatalogProperties.standard()),
                mock(com.gahyeonbot.application.life.CharacterMemoryStore.class));
        org.springframework.test.util.ReflectionTestUtils.invokeMethod(provider, "configureKnowledge", knowledge);
        org.springframework.test.util.ReflectionTestUtils.setField(provider, "ontologyRag", rag);
        String prompt = provider.systemPrompt(null,
                "character:gahyeon:gahyeon-home:actor:101|desktop:1", "새벽 담당자");
        assertThat(prompt).contains("온톨로지 근거 경로", "민지", "RESPONSIBLE_FOR", "source=", "원문:");
        String unauthorized = provider.systemPrompt(null,
                "character:gahyeon:gahyeon-home:actor:202|desktop:2", "새벽 담당자");
        assertThat(unauthorized).doesNotContain("민지", "RESPONSIBLE_FOR");
    }

    @Test void traversalHandlesCyclesAndReportsResultTruncation() {
        var other = new Entity("project:other", Type.PROJECT, "노을", List.of());
        String body = "오로라는 노을에 의존한다. 노을은 오로라에 의존한다.";
        ingestion.ingest(document("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE, body), new Document(1, List.of(
                new Claim(project(), Relation.DEPENDS_ON, other, "오로라는 노을에 의존한다."),
                new Claim(other, Relation.DEPENDS_ON, project(), "노을은 오로라에 의존한다."))));
        var report = graph.search(new OntologyGraphService.Query("gahyeon", null, "오로라", 1, 3));
        assertThat(report.paths()).hasSize(1);
        assertThat(report.truncated()).isTrue();
        assertThat(report.authorizedClaimsScanned()).isEqualTo(2);
    }

    @Test void graphAndLexicalMatchesDoNotDuplicateTheSameChunk() {
        addOwner("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        var found = rag.search(new KnowledgeBaseService.SearchRequest("gahyeon", null, "민지", 10));
        assertThat(found.results()).hasSize(1);
        assertThat(found.results().getFirst().content()).contains("원문:", "민지는 출시 검증을 맡았다.");
    }

    @Test void authorizedClaimScanHasHardLimitAndReportsIncompleteCoverage() {
        addOwner("gahyeon", null, KnowledgeBaseService.AccessScope.SERVICE);
        String original = jdbc.queryForObject("select id from knowledge_ontology_claims", String.class);
        List<Object[]> batch = new ArrayList<>();
        for (int i = 0; i < 2000; i++) batch.add(new Object[]{"copy-" + i, original});
        jdbc.batchUpdate("""
                insert into knowledge_ontology_claims
                (id, chunk_id, schema_version, subject_key, subject_type, subject_label, subject_aliases,
                 relation_type, object_key, object_type, object_label, object_aliases, evidence_quote)
                select ?, chunk_id, schema_version, subject_key, subject_type, subject_label, subject_aliases,
                       relation_type, object_key, object_type, object_label, object_aliases, evidence_quote
                from knowledge_ontology_claims where id = ?
                """, batch);
        var report = graph.search(query("gahyeon", null, "없는이름", 2));
        assertThat(report.authorizedClaimsScanned()).isEqualTo(2000);
        assertThat(report.paths()).isEmpty();
        assertThat(report.truncated()).isTrue();
    }

    private OntologyIngestionService.Result addProject(String service, String owner, KnowledgeBaseService.AccessScope scope) {
        return ingestion.ingest(document(service, owner, scope, "출시 검증은 오로라 프로젝트의 작업이다."),
                new Document(1, List.of(new Claim(task(), Relation.PART_OF, project(), "출시 검증은 오로라 프로젝트의 작업이다."))));
    }
    private OntologyIngestionService.Result addOwner(String service, String owner, KnowledgeBaseService.AccessScope scope) {
        return ingestion.ingest(document(service, owner, scope, "민지는 출시 검증을 맡았다."), ownerOntology());
    }
    private static Document ownerOntology() { return new Document(1, List.of(new Claim(person(), Relation.RESPONSIBLE_FOR, task(), "민지는 출시 검증을 맡았다."))); }
    private static Entity person() { return new Entity("person:minji", Type.PERSON, "민지", List.of()); }
    private static Entity task() { return new Entity("task:release-check", Type.TASK, "출시 검증", List.of()); }
    private static Entity project() { return new Entity("project:aurora", Type.PROJECT, "오로라", List.of("새벽")); }
    private static OntologyGraphService.Query query(String service, String owner, String query, int hops) {
        return new OntologyGraphService.Query(service, owner, query, 10, hops);
    }
    private static KnowledgeBaseService.IngestionRequest document(String service, String owner,
            KnowledgeBaseService.AccessScope scope, String body) {
        return new KnowledgeBaseService.IngestionRequest(service, owner, "text", "fixture", null, scope,
                "원문", "ko", body, "{}");
    }

    @Configuration
    @EnableTransactionManagement
    static class Config {
        @Bean DataSource dataSource() throws Exception {
            var source = new DriverManagerDataSource("jdbc:h2:mem:ontology-" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
            try (var connection = source.getConnection(); var statement = connection.createStatement()) {
                statement.execute("create table gahyeon_principals(id bigint primary key)");
                statement.execute("create table character_memories(id bigint primary key)");
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/migration/V41__Add_scoped_knowledge_and_identity_governance.sql"));
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/migration/V42__Add_evidence_backed_ontology.sql"));
            }
            return source;
        }
        @Bean JdbcTemplate jdbc(DataSource source) { return new JdbcTemplate(source); }
        @Bean PlatformTransactionManager transactionManager(DataSource source) { return new DataSourceTransactionManager(source); }
        @Bean ObjectMapper json() { return new ObjectMapper(); }
        @Bean KnowledgeBaseService knowledge(JdbcTemplate jdbc, ObjectProvider<KnowledgeEmbeddingPort> embeddings, ObjectMapper json) {
            return new KnowledgeBaseService(jdbc, embeddings, json);
        }
        @Bean OntologyGraphService graph(JdbcTemplate jdbc, ObjectMapper json) { return new OntologyGraphService(jdbc, json); }
        @Bean OntologyIngestionService ingestion(KnowledgeBaseService knowledge, OntologyGraphService graph, JdbcTemplate jdbc) {
            return new OntologyIngestionService(knowledge, graph, jdbc);
        }
        @Bean OntologyRagService rag(KnowledgeBaseService knowledge, OntologyGraphService graph) {
            return new OntologyRagService(knowledge, graph, true);
        }
    }
}
