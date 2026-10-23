package com.gahyeonbot.services.ai.agent.skills;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.tool.ToolDecision;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.spec.McpSchema;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.definition.ToolDefinition;

import java.util.*;

/** Uses the existing Spring AI BOM's MCP SDK; transport/auth remain operator configured. */
public final class McpSkillToolAdapter implements ApprovedMcpTools {
    private final List<AgentToolRegistry.Binding> bindings;

    public McpSkillToolAdapter(String serverId, McpSyncClient client, List<Grant> grants) {
        if (!serverId.matches("[a-z][a-z0-9-]{0,40}")) throw new IllegalArgumentException("Invalid MCP server id");
        if (!client.isInitialized()) throw new IllegalStateException("MCP connection must be initialized");
        List<AgentToolRegistry.Binding> tools = new ArrayList<>();
        Set<String> aliases = new HashSet<>();
        for (Grant grant : grants) {
            if (!aliases.add(grant.alias())) throw new IllegalArgumentException("Duplicate MCP alias");
            ToolCallback callback = new ToolCallback() {
                @Override public ToolDefinition getToolDefinition() {
                    return ToolDefinition.builder().name(grant.alias()).description(grant.description())
                            .inputSchema(grant.inputSchema()).build();
                }

                @Override public String call(String input) {
                    if (input == null || input.length() > 16000) throw new IllegalArgumentException("MCP arguments too large");
                    try {
                        ObjectMapper json = new ObjectMapper();
                        var args = json.readTree(input);
                        if (args == null || !args.isObject()) throw new IllegalArgumentException("MCP arguments must be an object");
                        McpSchema.Tool remote = findTool(client, grant.remoteName());
                        // SDK JsonSchema adds null-valued optional fields; normalize via its typed representation.
                        McpSchema.Tool pinned = new McpSchema.Tool(grant.remoteName(), grant.description(), grant.inputSchema());
                        if (!remote.inputSchema().equals(pinned.inputSchema()))
                            throw new IllegalStateException("MCP schema changed; review the grant before retrying");
                        var result = client.callTool(new McpSchema.CallToolRequest(grant.remoteName(), input));
                        if (result == null || Boolean.TRUE.equals(result.isError()))
                            throw new IllegalStateException("MCP tool returned an error");
                        if (result.content() == null || result.content().isEmpty()
                                || result.content().stream().anyMatch(item -> !(item instanceof McpSchema.TextContent)))
                            throw new IllegalStateException("Only nonempty MCP text results are supported");
                        String text = result.content().stream().map(item -> ((McpSchema.TextContent) item).text())
                                .filter(Objects::nonNull).reduce((left, right) -> left + "\n" + right).orElse("");
                        if (text.isBlank() || text.length() > 64000)
                            throw new IllegalStateException("MCP result empty or above the approved size limit");
                        return text;
                    } catch (java.io.IOException failure) {
                        throw new IllegalArgumentException("Invalid MCP argument JSON");
                    }
                }
            };
            tools.add(new AgentToolRegistry.Binding("mcp:" + serverId, callback, grant.decision(),
                    grant.allowedActors(), grant.toolScopeId()));
        }
        bindings = List.copyOf(tools);
    }

    @Override public List<AgentToolRegistry.Binding> bindings() { return bindings; }

    private static McpSchema.Tool findTool(McpSyncClient client, String name) {
        String cursor = null;
        Set<String> seenCursors = new HashSet<>();
        for (int page = 0; page < 16; page++) {
            var result = client.listTools(cursor);
            if (result == null || result.tools() == null) throw new IllegalStateException("Invalid MCP discovery result");
            var matches = result.tools().stream().filter(tool -> name.equals(tool.name())).toList();
            if (matches.size() > 1) throw new IllegalStateException("Ambiguous MCP tool name");
            if (matches.size() == 1) return matches.getFirst();
            cursor = result.nextCursor();
            if (cursor == null || cursor.isBlank()) break;
            if (!seenCursors.add(cursor)) throw new IllegalStateException("MCP discovery cursor repeated");
        }
        throw new IllegalStateException("Approved MCP tool unavailable");
    }

    public record Grant(String alias, String remoteName, String description, String inputSchema,
            ToolDecision decision, Set<Long> allowedActors, Long toolScopeId) {
        public Grant {
            if (alias == null || remoteName == null || remoteName.isBlank()
                    || description == null || description.isBlank() || inputSchema == null)
                throw new IllegalArgumentException("MCP grant requires locally reviewed metadata");
            Objects.requireNonNull(decision);
            allowedActors = Set.copyOf(allowedActors);
            if (allowedActors.isEmpty() || toolScopeId == null) throw new IllegalArgumentException("Explicit MCP scope required");
        }
    }
}
