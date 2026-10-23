package com.gahyeonbot.services.ai.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Local QA only: exports ledger timestamps without prompts, responses or tool payloads. */
@Component
@Profile("dev")
@ConditionalOnProperty(name = "gahyeon.diagnostics.latency", havingValue = "true")
public class AgentLatencyDiagnostics {
    private static final Logger log = LoggerFactory.getLogger(AgentLatencyDiagnostics.class);
    private final JdbcTemplate jdbc;
    private long cursor;
    public AgentLatencyDiagnostics(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    @Scheduled(fixedDelay = 1000, initialDelay = 5000)
    public void export() {
        var rows = jdbc.queryForList("SELECT id, run_id, event_type, step, tool_name, created_at FROM agent_run_events WHERE id > ? ORDER BY id LIMIT 200", cursor);
        for (var row : rows) {
            log.info("LATENCY_EVENT run={} event={} step={} tool={} at={}", row.get("run_id"),
                    row.get("event_type"), row.get("step"), row.get("tool_name"), row.get("created_at"));
            cursor = ((Number) row.get("id")).longValue();
        }
    }
}
