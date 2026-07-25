package com.gahyeonbot.services.ai.agent;

public interface AgentBackgroundHandler {
    String jobType();

    String execute(String payload) throws Exception;
}
