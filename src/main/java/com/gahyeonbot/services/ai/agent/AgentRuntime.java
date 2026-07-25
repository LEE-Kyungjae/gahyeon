package com.gahyeonbot.services.ai.agent;

public interface AgentRuntime {
    AgentResult execute(AgentRequest request);

    AgentResult resume(String runId, long actorUserId);

    AgentResult resumeBackground(String runId, String backgroundResult);
}
