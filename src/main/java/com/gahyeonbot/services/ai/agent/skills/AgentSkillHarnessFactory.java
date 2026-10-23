package com.gahyeonbot.services.ai.agent.skills;

import com.gahyeonbot.core.tool.ToolPolicy;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

@Component
public final class AgentSkillHarnessFactory {
    private final AgentSkillCatalog catalog;
    private final AgentSkillJournal journal;
    private final List<ApprovedMcpTools> mcp;
    private final boolean enabled;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private List<RequestScopedTools> requestTools = List.of();

    public AgentSkillHarnessFactory(AgentSkillCatalog catalog, AgentSkillJournal journal,
            List<ApprovedMcpTools> mcp, @Value("${gahyeon.agent.skills.enabled:false}") boolean enabled) {
        this.catalog = catalog;
        this.journal = journal;
        this.mcp = List.copyOf(mcp);
        this.enabled = enabled;
    }

    public AgentSkillHarness open(String runId, AgentRequest request, ToolCallback[] nativeTools, ToolPolicy policy) {
        if (!enabled) return null;
        List<AgentToolRegistry.Binding> bindings = new ArrayList<>();
        for (ToolCallback callback : nativeTools) bindings.add(new AgentToolRegistry.Binding(
                "native", callback, policy.decide(callback.getToolDefinition().name()), Set.of(), null));
        mcp.forEach(provider -> bindings.addAll(provider.bindings()));
        requestTools.forEach(provider -> bindings.addAll(provider.bindings(request)));
        var harness = new AgentSkillHarness(runId, request.actorId().value(), request.toolScopeId(), catalog,
                new AgentToolRegistry(bindings), journal);
        String intent = request.message().toLowerCase(java.util.Locale.ROOT);
        boolean copperPrice = intent.contains("lme") && (intent.contains("구리") || intent.contains("copper"))
                && (intent.contains("가격") || intent.contains("시세") || intent.contains("price"));
        boolean researchAvailable = Set.of("research_search", "research_read", "research_verify").stream()
                .allMatch(name -> bindings.stream().anyMatch(binding -> binding.name().equals(name)
                        && binding.availableTo(request.actorId().value(), request.toolScopeId())));
        if (copperPrice && researchAvailable && journal.read(runId).isEmpty()) {
            // Original authenticated request only. Existing select still checks tool authority.
            harness.select("web-research", "1.0.0");
        }
        return harness;
    }

    /** A paused skilled run cannot silently resume in legacy mode after a feature rollback. */
    public AgentSkillHarness openForRun(com.gahyeonbot.entity.AgentRun run, AgentRequest request,
            ToolCallback[] nativeTools, ToolPolicy policy) {
        if (!enabled && run.getCurrentStep() > 0 && !journal.read(run.getId()).isEmpty()) {
            throw new IllegalStateException("Skill execution disabled; restart the paused request explicitly");
        }
        return open(run.getId(), request, nativeTools, policy);
    }
}
