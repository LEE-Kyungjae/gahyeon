package com.gahyeonbot.services.ai.agent;

public record AgentBackgroundClaim(
        String jobId,
        String runId,
        String jobType,
        String payload
) {}
