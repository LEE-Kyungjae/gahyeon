package com.gahyeonbot.services.ai.agent.work;

import com.gahyeonbot.core.tool.ToolDecision;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import com.gahyeonbot.services.ai.agent.skills.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.util.List;
import java.util.Set;

@Component
public final class WebResearchTools implements RequestScopedTools {
    private final boolean enabled;
    public WebResearchTools(@Value("${gahyeon.agent.research.enabled:false}") boolean enabled) { this.enabled = enabled; }
    public List<AgentToolRegistry.Binding> bindings(AgentRequest request) {
        if (!enabled) return List.of();
        return new WebResearchSession(new PublicWebClient()::get, request.message()).tools().stream().map(callback ->
                new AgentToolRegistry.Binding("native", callback, ToolDecision.ALLOW,
                        Set.of(request.actorId().value()), request.toolScopeId())).toList();
    }
}
