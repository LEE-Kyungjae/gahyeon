package com.gahyeonbot.services.ai.agent;

import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class AgentToolPolicy {
    private static final Map<String, AgentToolRisk> DEFAULT_RISKS = Map.of(
            "get_current_weather", AgentToolRisk.EXTERNAL_READ,
            "get_weather_forecast", AgentToolRisk.EXTERNAL_READ,
            "get_supported_weather_locations", AgentToolRisk.READ_ONLY,
            "get_collected_github_trending", AgentToolRisk.READ_ONLY,
            "get_collected_github_repository", AgentToolRisk.READ_ONLY,
            "search_collected_github_repositories", AgentToolRisk.READ_ONLY,
            "search_collected_ai_papers", AgentToolRisk.READ_ONLY,
            "search_recent_collected_ai_papers", AgentToolRisk.READ_ONLY,
            "get_collected_ai_paper_by_arxiv_id", AgentToolRisk.READ_ONLY,
            "get_internal_knowledge_freshness", AgentToolRisk.READ_ONLY
    );
    private final Map<String, AgentToolRisk> risks;

    public AgentToolPolicy() {
        this(DEFAULT_RISKS);
    }

    AgentToolPolicy(Map<String, AgentToolRisk> risks) {
        this.risks = Map.copyOf(risks);
    }

    public AgentToolDecision decide(AgentGateway gateway, String toolName) {
        AgentToolRisk risk = risks.get(toolName);
        if (risk == null) return AgentToolDecision.DENY;
        return switch (risk) {
            case READ_ONLY, EXTERNAL_READ -> AgentToolDecision.ALLOW;
            case WRITE -> AgentToolDecision.REQUIRE_APPROVAL;
            case DESTRUCTIVE -> AgentToolDecision.DENY;
        };
    }

    public AgentToolRisk riskOf(String toolName) {
        return risks.get(toolName);
    }
}
