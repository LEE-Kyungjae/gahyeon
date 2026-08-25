package com.gahyeonbot.application.life;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import static org.assertj.core.api.Assertions.*;

class CharacterAutonomyWorkspaceServiceTest {
    private JdbcTemplate jdbc;
    private CharacterAutonomyWorkspaceService service;

    @BeforeEach
    void setUp() {
        var dataSource = new DriverManagerDataSource("jdbc:h2:mem:workspace;MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
        jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("drop all objects");
        jdbc.execute("""
                create table character_identity_revisions (
                  id varchar(36), character_id varchar(64), revision bigint, soul_markdown clob,
                  created_by_subject_id varchar(160), created_at timestamp with time zone,
                  activated_at timestamp with time zone, retired_at timestamp with time zone)
                """);
        jdbc.execute("""
                create table character_autonomy_todos (
                  id varchar(36), character_id varchar(64), world_id varchar(100), owner_subject_id varchar(160),
                  description varchar(1000), status varchar(24), not_before timestamp with time zone,
                  created_at timestamp with time zone, updated_at timestamp with time zone)
                """);
        jdbc.execute("""
                create table memory_graph_nodes (
                  id varchar(36), character_id varchar(64), world_id varchar(100), owner_subject_id varchar(160),
                  node_type varchar(32), node_key varchar(240), label varchar(500), properties_json clob,
                  created_at timestamp with time zone, updated_at timestamp with time zone)
                """);
        jdbc.execute("""
                create table memory_graph_edges (
                  id varchar(36), character_id varchar(64), world_id varchar(100), owner_subject_id varchar(160),
                  from_node_id varchar(36), to_node_id varchar(36), relation_type varchar(64), weight double,
                  evidence_memory_id bigint, created_at timestamp with time zone, updated_at timestamp with time zone)
                """);
        service = new CharacterAutonomyWorkspaceService(jdbc);
    }

    @Test
    void soulRevisionsAreImmutableAndOnlyExplicitlyActivatedRevisionIsRead() {
        var first = service.createSoulRevision("gahyeon", "차분한 가현", "zezestudio:admin");
        var second = service.createSoulRevision("gahyeon", "따뜻하고 솔직한 가현", "zezestudio:admin");

        assertThat(service.activeSoul("gahyeon")).isEmpty();
        service.activateSoulRevision("gahyeon", second.revision());

        assertThat(service.activeSoul("gahyeon")).get()
                .extracting(CharacterAutonomyWorkspaceService.SoulRevision::soulMarkdown)
                .isEqualTo("따뜻하고 솔직한 가현");
        assertThat(first.revision()).isEqualTo(1);
        assertThat(second.revision()).isEqualTo(2);
    }

    @Test
    void todosAreClaimedOnceAndCompletedInOrder() {
        var todo = service.addTodo("gahyeon", "home", "zezestudio:user", "안부 확인");

        var claimed = service.claimDueTodo("gahyeon", "home");
        assertThat(claimed).get().extracting(CharacterAutonomyWorkspaceService.Todo::id).isEqualTo(todo.id());
        assertThat(service.claimDueTodo("gahyeon", "home")).isEmpty();

        service.completeTodo(todo.id(), true);
        assertThat(jdbc.queryForObject("select status from character_autonomy_todos where id = ?",
                String.class, todo.id())).isEqualTo("COMPLETED");
    }

    @Test
    void graphEdgesCannotCrossUserNamespaces() {
        var userA = service.upsertGraphNode("gahyeon", "home", "zezestudio:a", "person", "self", "A", "{}");
        var topicA = service.upsertGraphNode("gahyeon", "home", "zezestudio:a", "topic", "coffee", "커피", "{}");
        var userB = service.upsertGraphNode("gahyeon", "home", "zezestudio:b", "person", "self", "B", "{}");

        assertThat(service.connectGraphNodes("gahyeon", "home", "zezestudio:a",
                userA.id(), topicA.id(), "LIKES", .8, null).relationType()).isEqualTo("LIKES");
        assertThatThrownBy(() -> service.connectGraphNodes("gahyeon", "home", "zezestudio:a",
                userA.id(), userB.id(), "KNOWS", .5, null)).isInstanceOf(IllegalArgumentException.class);
    }
}
