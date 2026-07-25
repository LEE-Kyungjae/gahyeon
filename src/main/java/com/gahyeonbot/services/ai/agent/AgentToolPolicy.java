package com.gahyeonbot.services.ai.agent;

import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class AgentToolPolicy {
    private static final Map<String, AgentToolRisk> RISKS = Map.of(
            "get_current_weather", AgentToolRisk.EXTERNAL_READ,
            "get_weather_forecast", AgentToolRisk.EXTERNAL_READ,
            "get_supported_weather_locations", AgentToolRisk.READ_ONLY,
            "get_collected_github_trending", AgentToolRisk.READ_ONLY,
            "get_collected_github_repository", AgentToolRisk.READ_ONLY,
            "search_collected_github_repositories", AgentToolRisk.READ_ONLY,
            "search_collected_ai_papers", AgentToolRisk.READ_ONLY,
            "get_internal_knowledge_freshness", AgentToolRisk.READ_ONLY
    );

    public AgentToolDecision decide(AgentGateway gateway, String toolName) {
        AgentToolRisk risk = RISKS.get(toolName);
        if (risk == null) return AgentToolDecision.DENY;
        return switch (risk) {
            case READ_ONLY, EXTERNAL_READ -> AgentToolDecision.ALLOW;
            case WRITE -> AgentToolDecision.REQUIRE_APPROVAL;
            case DESTRUCTIVE -> AgentToolDecision.DENY;
        };
    }

    public AgentToolRisk riskOf(String toolName) {
        return RISKS.get(toolName);
    }
}
