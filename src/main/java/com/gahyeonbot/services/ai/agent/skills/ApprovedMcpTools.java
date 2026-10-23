package com.gahyeonbot.services.ai.agent.skills;

import java.util.List;

/** Supplied by an explicitly configured connection; discovery alone never grants authority. */
public interface ApprovedMcpTools {
    List<AgentToolRegistry.Binding> bindings();
}
