package com.gahyeonbot.services.ai.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;

final class RecoverableToolOutputCompressor {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final int DEFAULT_LIMIT = 12_000;

    private RecoverableToolOutputCompressor() {}

    static CompressionResult compress(String toolName, String output, ToolOutputArchive archive) {
        return compress(toolName, output, DEFAULT_LIMIT, archive);
    }

    static CompressionResult compress(
            String toolName, String output, int characterLimit, ToolOutputArchive archive) {
        String original = output == null ? "" : output;
        Objects.requireNonNull(archive, "tool output archive");
        if (characterLimit < 256) throw new IllegalArgumentException("characterLimit must be at least 256");

        String compactJson = compactJson(original);
        if (compactJson.length() <= characterLimit) {
            String content = compactJson.length() < original.length() ? compactJson : original;
            return new CompressionResult(content, digest(original), false, original.length());
        }

        String digest = digest(original);
        String marker = "\n…[tool-output truncated; sha256=" + digest
                + "; original_chars=" + original.length() + "]…\n";
        int remaining = characterLimit - marker.length();
        if (remaining <= 0) return new CompressionResult(original, digest, false, original.length());

        int head = remaining / 2;
        int tail = remaining - head;
        String compressed = original.substring(0, head) + marker
                + original.substring(original.length() - tail);
        if (compressed.length() >= original.length()) {
            return new CompressionResult(original, digest, false, original.length());
        }

        archive.store(digest, toolName == null ? "" : toolName, original);
        if (archive.retrieve(digest).filter(original::equals).isEmpty()) {
            throw new IllegalStateException("archived tool output failed recovery verification");
        }
        return new CompressionResult(compressed, digest, true, original.length());
    }

    private static String compactJson(String source) {
        try {
            JsonNode node = JSON.readTree(source);
            return node == null ? source : JSON.writeValueAsString(node);
        } catch (Exception ignored) {
            return source;
        }
    }

    private static String digest(String value) {
        try {
            byte[] bytes = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(bytes);
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 unavailable", impossible);
        }
    }

    record CompressionResult(String modelContent, String originalDigest, boolean compressed,
                             int originalCharacters) {}
}
