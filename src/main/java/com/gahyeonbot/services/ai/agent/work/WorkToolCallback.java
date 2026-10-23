package com.gahyeonbot.services.ai.agent.work;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.definition.ToolDefinition;
import java.util.function.Function;

final class WorkToolCallback implements ToolCallback {
    private final ToolDefinition definition;
    private final Function<JsonNode, Object> action;
    private static final ObjectMapper JSON = new ObjectMapper();
    WorkToolCallback(String name, String description, String schema, Function<JsonNode, Object> action) {
        this.definition = ToolDefinition.builder().name(name).description(description).inputSchema(schema).build();
        this.action = action;
    }
    public ToolDefinition getToolDefinition() { return definition; }
    public String call(String input) {
        try {
            if (input == null || input.length() > 64000) throw new IllegalArgumentException("Arguments too large");
            JsonNode args = JSON.readTree(input);
            if (!args.isObject()) throw new IllegalArgumentException("Expected object");
            return JSON.writeValueAsString(action.apply(args));
        } catch (java.io.IOException e) { throw new IllegalArgumentException("Invalid tool JSON"); }
    }
    static String text(JsonNode args, String key, int limit) {
        var value = args.path(key);
        if (!value.isTextual() || value.asText().isBlank() || value.asText().length() > limit)
            throw new IllegalArgumentException("Invalid " + key);
        return value.asText();
    }
    static void keys(JsonNode args, String... allowed) {
        var names = java.util.Set.of(allowed);
        args.fieldNames().forEachRemaining(key -> {
            if (!names.contains(key)) throw new IllegalArgumentException("Unknown argument: " + key);
        });
    }
}
