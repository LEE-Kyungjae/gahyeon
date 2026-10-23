package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.List;
import java.util.Map;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class AgentLatencyDiagnosticsTest {
    @Test void exportsOnlyMetadataAndAdvancesCursor() {
        var jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), eq(0L))).thenReturn(List.of(Map.of(
                "id", 7L, "run_id", "fixture", "event_type", "MODEL_CALL_STARTED", "step", 1,
                "tool_name", "null", "created_at", "2026-10-18 00:00:00")));
        when(jdbc.queryForList(anyString(), eq(7L))).thenReturn(List.of());
        var exporter = new AgentLatencyDiagnostics(jdbc);
        exporter.export(); exporter.export();
        verify(jdbc).queryForList(eq("SELECT id, run_id, event_type, step, tool_name, created_at FROM agent_run_events WHERE id > ? ORDER BY id LIMIT 200"), eq(0L));
        verify(jdbc).queryForList(anyString(), eq(7L));
        verifyNoMoreInteractions(jdbc);
    }
}
