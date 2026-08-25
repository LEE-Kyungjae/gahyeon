package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

class RecoverableToolOutputCompressorTest {
    @Test
    void neverGrowsSmallOutput() {
        var result = RecoverableToolOutputCompressor.compress(
                "weather", "sunny", 256, noOpArchive());

        assertThat(result.compressed()).isFalse();
        assertThat(result.modelContent()).isEqualTo("sunny");
    }

    @Test
    void compactsJsonLosslesslyBeforeConsideringTruncation() {
        String output = "{\n  \"temperature\": 23,\n  \"condition\": \"sunny\"\n}";
        var result = RecoverableToolOutputCompressor.compress(
                "weather", output, 256, noOpArchive());

        assertThat(result.compressed()).isFalse();
        assertThat(result.modelContent()).isEqualTo("{\"temperature\":23,\"condition\":\"sunny\"}");
        assertThat(result.modelContent().length()).isLessThan(output.length());
    }

    @Test
    void archivesExactOriginalWhenLargeOutputIsTruncated() {
        String output = "begin\n" + "diagnostic-line\n".repeat(200) + "end";
        Map<String, String> stored = new HashMap<>();
        ToolOutputArchive archive = new ToolOutputArchive() {
            @Override
            public void store(String digest, String tool, String original) {
                stored.put(digest, original);
            }

            @Override
            public Optional<String> retrieve(String digest) {
                return Optional.ofNullable(stored.get(digest));
            }
        };

        var result = RecoverableToolOutputCompressor.compress(
                "diagnostics", output, 300,
                archive);

        assertThat(result.compressed()).isTrue();
        assertThat(result.modelContent().length()).isLessThanOrEqualTo(300);
        assertThat(result.modelContent()).contains("sha256=" + result.originalDigest());
        assertThat(stored.get(result.originalDigest())).isEqualTo(output);
    }

    private static ToolOutputArchive noOpArchive() {
        return new ToolOutputArchive() {
            @Override public void store(String digest, String tool, String original) {}
            @Override public Optional<String> retrieve(String digest) { return Optional.empty(); }
        };
    }
}
