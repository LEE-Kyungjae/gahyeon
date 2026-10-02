package com.gahyeonbot.core.tool;

import java.util.Map;

public class ToolPolicy {
    private static final Map<String, ToolRisk> DEFAULT_RISKS = Map.ofEntries(
            Map.entry("get_current_weather", ToolRisk.EXTERNAL_READ),
            Map.entry("get_weather_forecast", ToolRisk.EXTERNAL_READ),
            Map.entry("get_supported_weather_locations", ToolRisk.READ_ONLY),
            Map.entry("get_collected_github_trending", ToolRisk.READ_ONLY),
            Map.entry("get_collected_github_repository", ToolRisk.READ_ONLY),
            Map.entry("search_collected_github_repositories", ToolRisk.READ_ONLY),
            Map.entry("search_collected_ai_papers", ToolRisk.READ_ONLY),
            Map.entry("search_recent_collected_ai_papers", ToolRisk.READ_ONLY),
            Map.entry("get_collected_ai_paper_by_arxiv_id", ToolRisk.READ_ONLY),
            Map.entry("get_internal_knowledge_freshness", ToolRisk.READ_ONLY),
            Map.entry("get_recent_personalized_news", ToolRisk.READ_ONLY)
    );
    private final Map<String, ToolRisk> risks;

    public ToolPolicy() {
        this(DEFAULT_RISKS);
    }

    ToolPolicy(Map<String, ToolRisk> risks) {
        this.risks = Map.copyOf(risks);
    }

    public ToolDecision decide(String toolName) {
        ToolRisk risk = risks.get(toolName);
        if (risk == null) return ToolDecision.DENY;
        return switch (risk) {
            case READ_ONLY, EXTERNAL_READ -> ToolDecision.ALLOW;
            case WRITE -> ToolDecision.REQUIRE_APPROVAL;
            case DESTRUCTIVE -> ToolDecision.DENY;
        };
    }

    public ToolRisk riskOf(String toolName) {
        return risks.get(toolName);
    }
}
