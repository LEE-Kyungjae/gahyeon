package com.gahyeonbot.services.ai.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;

import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

final class SensitiveDataRedactor {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String REDACTED = "[REDACTED]";
    private static final int MAX_AUDIT_CHARACTERS = 8_192;
    private static final Set<String> SENSITIVE_KEYS = Set.of(
            "password", "passwd", "pwd", "secret", "token", "accesstoken", "refreshtoken",
            "authorization", "cookie", "setcookie", "apikey", "privatekey", "clientsecret",
            "credential", "credentials");
    private static final Pattern BEARER = Pattern.compile(
            "(?i)\\bBearer\\s+[A-Za-z0-9._~+/-]+=*");
    private static final Pattern UNIX_HOME = Pattern.compile("/(?:Users|home)/[^/\\s]+(?=/|\\b)");
    private static final Pattern WINDOWS_HOME = Pattern.compile(
            "(?i)[A-Z]:\\\\Users\\\\[^\\\\\\s]+(?=\\\\|\\b)");
    private static final Pattern SECRET_ASSIGNMENT = Pattern.compile(
            "(?i)(password|passwd|pwd|secret|token|api[_-]?key|authorization)\\s*[:=]\\s*([^,;\\s}]+)");

    private SensitiveDataRedactor() {}

    static String redact(String value) {
        String source = value == null ? "" : value;
        String redacted;
        try {
            JsonNode root = JSON.readTree(source);
            redactNode(root);
            redacted = JSON.writeValueAsString(root);
        } catch (Exception ignored) {
            redacted = redactText(source);
        }
        if (redacted.length() > MAX_AUDIT_CHARACTERS) {
            redacted = redacted.substring(0, MAX_AUDIT_CHARACTERS) + "…[TRUNCATED]";
        }
        return redacted;
    }

    private static void redactNode(JsonNode node) {
        if (node instanceof ObjectNode object) {
            Iterator<Map.Entry<String, JsonNode>> fields = object.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                if (isSensitive(field.getKey())) {
                    object.put(field.getKey(), REDACTED);
                } else if (field.getValue().isTextual()) {
                    object.put(field.getKey(), redactText(field.getValue().textValue()));
                } else {
                    redactNode(field.getValue());
                }
            }
        } else if (node instanceof ArrayNode array) {
            for (int index = 0; index < array.size(); index++) {
                JsonNode child = array.get(index);
                if (child.isTextual()) array.set(index, TextNode.valueOf(redactText(child.textValue())));
                else redactNode(child);
            }
        }
    }

    private static boolean isSensitive(String key) {
        String normalized = key == null ? "" : key.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return SENSITIVE_KEYS.stream().anyMatch(normalized::contains);
    }

    private static String redactText(String value) {
        String redacted = BEARER.matcher(value).replaceAll("Bearer " + REDACTED);
        redacted = SECRET_ASSIGNMENT.matcher(redacted).replaceAll("$1=" + REDACTED);
        redacted = UNIX_HOME.matcher(redacted).replaceAll("/[HOME]");
        return WINDOWS_HOME.matcher(redacted).replaceAll("[HOME]");
    }
}
