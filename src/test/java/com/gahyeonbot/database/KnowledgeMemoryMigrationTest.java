package com.gahyeonbot.database;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ScriptUtils;

import static org.assertj.core.api.Assertions.assertThat;

class KnowledgeMemoryMigrationTest {
    @Test
    void v41AppliesCleanlyAndCreatesEveryGovernanceTable() throws Exception {
        var dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:v41;MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
        try (var connection = dataSource.getConnection(); var statement = connection.createStatement()) {
            statement.execute("create table gahyeon_principals (id bigint primary key)");
            statement.execute("create table character_memories (id bigint primary key)");
            ScriptUtils.executeSqlScript(connection,
                    new ClassPathResource("db/migration/V41__Add_scoped_knowledge_and_identity_governance.sql"));
            try (var tables = connection.getMetaData().getTables(null, null, "%", new String[]{"TABLE"})) {
                java.util.Set<String> names = new java.util.HashSet<>();
                while (tables.next()) names.add(tables.getString("TABLE_NAME").toLowerCase());
                assertThat(names).contains(
                        "knowledge_sources", "knowledge_documents", "knowledge_chunks",
                        "memory_identity_merge_requests", "privacy_deletion_jobs",
                        "character_identity_revisions", "character_autonomy_todos",
                        "memory_graph_nodes", "memory_graph_edges", "character_heartbeat_runs");
            }
        }
    }
}
