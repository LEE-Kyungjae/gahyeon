package com.gahyeonbot.services.ai.agent;

import java.time.LocalDateTime;
import java.util.List;

public record AgentRunView(
        String runId,
        AgentRunStatus status,
        int currentStep,
        int maxSteps,
        String input,
        String output,
        String errorCode,
        LocalDateTime updatedAt,
        List<ApprovalView> approvals
) {
    public record ApprovalView(
            String approvalId,
            String toolName,
            AgentApprovalStatus status
    ) {}
}
