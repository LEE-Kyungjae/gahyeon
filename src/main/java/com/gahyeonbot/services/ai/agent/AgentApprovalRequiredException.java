package com.gahyeonbot.services.ai.agent;

import lombok.Getter;

@Getter
public class AgentApprovalRequiredException extends RuntimeException {
    private final String runId;
    private final String toolName;
    private final String arguments;

    public AgentApprovalRequiredException(String runId, String toolName, String arguments) {
        super("도구 실행 승인이 필요합니다: " + toolName);
        this.runId = runId;
        this.toolName = toolName;
        this.arguments = arguments;
    }
}
