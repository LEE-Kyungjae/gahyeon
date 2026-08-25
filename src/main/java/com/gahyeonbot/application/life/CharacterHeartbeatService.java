package com.gahyeonbot.application.life;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class CharacterHeartbeatService {
    private final CharacterAutonomyWorkspaceService workspace;
    private final JdbcTemplate jdbc;
    private final boolean enabled;
    private final ObjectProvider<CharacterTodoExecutionPort> executor;
    private final String characterId;
    private final String worldId;

    public CharacterHeartbeatService(CharacterAutonomyWorkspaceService workspace, JdbcTemplate jdbc,
            ObjectProvider<CharacterTodoExecutionPort> executor,
            @Value("${gahyeon.autonomy.enabled:false}") boolean enabled,
            @Value("${gahyeon.autonomy.character-id:gahyeon}") String characterId,
            @Value("${gahyeon.autonomy.world-id:gahyeon-home}") String worldId) {
        this.workspace = workspace;
        this.jdbc = jdbc;
        this.executor = executor;
        this.enabled = enabled;
        this.characterId = characterId;
        this.worldId = worldId;
    }

    @Scheduled(fixedDelayString = "${gahyeon.autonomy.heartbeat-millis:60000}")
    public void heartbeat() {
        if (!enabled) return;
        String runId = UUID.randomUUID().toString();
        CharacterTodoExecutionPort available = executor.getIfAvailable();
        var todo = available != null && available.isReady()
                ? workspace.claimDueTodo(characterId, worldId) : java.util.Optional.<CharacterAutonomyWorkspaceService.Todo>empty();
        String status = "NO_WORK";
        String failureClass = null;
        if (todo.isPresent()) {
            try {
                available.execute(todo.get());
                workspace.completeTodo(todo.get().id(), true);
                status = "COMPLETED";
            } catch (RuntimeException failure) {
                workspace.completeTodo(todo.get().id(), false);
                status = "FAILED";
                failureClass = failure.getClass().getSimpleName();
            }
        }
        jdbc.update("""
                insert into character_heartbeat_runs
                (id, character_id, world_id, status, claimed_todo_id, started_at, completed_at, failure_class)
                values (?, ?, ?, ?, ?, current_timestamp, current_timestamp, ?)
                """, runId, characterId, worldId, status,
                todo.map(CharacterAutonomyWorkspaceService.Todo::id).orElse(null), failureClass);
    }
}
