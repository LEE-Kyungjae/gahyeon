package com.gahyeonbot.services.ai.agent;

import java.time.Duration;
import java.util.List;

public record AgentResult(String runId, String content, List<String> tools, Duration duration) {
    public AgentResult {
        tools = tools == null ? List.of() : List.copyOf(tools);
    }
}
