package com.gahyeonbot.services.ai.agent;

public enum AgentRunStatus {
    QUEUED,
    RUNNING,
    WAITING_APPROVAL,
    WAITING_BACKGROUND,
    SUCCEEDED,
    FAILED,
    CANCELLED;

    public boolean terminal() {
        return this == SUCCEEDED || this == FAILED || this == CANCELLED;
    }
}
