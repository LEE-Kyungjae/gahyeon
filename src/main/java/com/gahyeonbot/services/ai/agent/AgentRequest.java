package com.gahyeonbot.services.ai.agent;

public record AgentRequest(
        String requestId,
        String sessionKey,
        AgentGateway gateway,
        Long guildId,
        Long userId,
        String username,
        String message,
        int maxSteps
) {
    public AgentRequest {
        if (requestId == null || requestId.isBlank()) throw new IllegalArgumentException("requestId가 필요합니다.");
        if (sessionKey == null || sessionKey.isBlank()) throw new IllegalArgumentException("sessionKey가 필요합니다.");
        if (gateway == null) throw new IllegalArgumentException("gateway가 필요합니다.");
        if (userId == null) throw new IllegalArgumentException("userId가 필요합니다.");
        if (message == null || message.isBlank()) throw new IllegalArgumentException("message가 필요합니다.");
        username = username == null || username.isBlank() ? "unknown" : username;
        message = message.trim();
        if (maxSteps < 1 || maxSteps > 32) throw new IllegalArgumentException("maxSteps는 1~32여야 합니다.");
    }

    public AgentRunRequest toRunRequest() {
        return new AgentRunRequest(
                requestId, sessionKey, gateway, guildId, userId, username, message, maxSteps);
    }
}
