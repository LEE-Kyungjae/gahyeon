package com.gahyeonbot.services.ai.agent.skills;

import com.gahyeonbot.core.tool.ToolDecision;
import org.springframework.ai.tool.ToolCallback;

import java.util.*;

/** Operator-controlled tool authority, independent of skill text and remote annotations. */
public final class AgentToolRegistry {
    private final Map<String, Binding> bindings;

    public AgentToolRegistry(Collection<Binding> tools) {
        Map<String, Binding> indexed = new LinkedHashMap<>();
        for (Binding binding : tools) {
            if (indexed.putIfAbsent(binding.name(), binding) != null)
                throw new IllegalArgumentException("Duplicate tool name: " + binding.name());
        }
        bindings = Collections.unmodifiableMap(indexed);
    }

    public Collection<Binding> all() { return bindings.values(); }

    public Binding require(String name) {
        Binding binding = bindings.get(name);
        if (binding == null) throw new IllegalArgumentException("Unregistered tool: " + name);
        return binding;
    }

    public record Binding(String source, ToolCallback callback, ToolDecision decision,
            Set<Long> allowedActors, Long toolScopeId) {
        public Binding {
            Objects.requireNonNull(callback);
            Objects.requireNonNull(decision);
            allowedActors = Set.copyOf(allowedActors);
            if (source == null || !(source.equals("native") || source.matches("mcp:[a-z][a-z0-9-]{0,40}")))
                throw new IllegalArgumentException("Tool source must be explicit");
            String name = callback.getToolDefinition().name();
            if (!name.matches("[a-zA-Z][a-zA-Z0-9_]{0,63}") || name.startsWith("agent_skill_"))
                throw new IllegalArgumentException("Invalid or reserved tool name");
            if (source.startsWith("mcp:") && (allowedActors.isEmpty() || toolScopeId == null))
                throw new IllegalArgumentException("MCP requires an explicit actor and scope grant");
        }

        public String name() { return callback.getToolDefinition().name(); }
        public boolean availableTo(long actor, Long scope) {
            return decision != ToolDecision.DENY
                    && (allowedActors.isEmpty() || allowedActors.contains(actor))
                    && (toolScopeId == null || toolScopeId.equals(scope));
        }
    }
}
