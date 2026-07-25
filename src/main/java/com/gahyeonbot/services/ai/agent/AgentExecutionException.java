package com.gahyeonbot.services.ai.agent;

import lombok.Getter;

@Getter
public class AgentExecutionException extends RuntimeException {
    private final String runId;
    private final String errorCode;

    public AgentExecutionException(String runId, String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.runId = runId;
        this.errorCode = errorCode;
    }
}
