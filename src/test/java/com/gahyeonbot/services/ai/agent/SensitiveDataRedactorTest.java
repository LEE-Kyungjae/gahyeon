package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class SensitiveDataRedactorTest {
    @Test
    void removesNestedCredentialsBearerTokensAndHomePaths() {
        String source = """
                {"path":"/Users/ze/private/file.txt","nested":{"access_token":"abc123"},
                 "headers":{"Authorization":"Bearer live-token"},"safe":"keep"}
                """;

        String redacted = SensitiveDataRedactor.redact(source);

        assertThat(redacted).contains("[REDACTED]", "[HOME]", "keep")
                .doesNotContain("abc123", "live-token", "/Users/ze");
    }

    @Test
    void redactsSensitiveAssignmentsInNonJsonArguments() {
        String redacted = SensitiveDataRedactor.redact(
                "deploy password=hunter2 Authorization:Bearer abc /home/gahyeon/config");

        assertThat(redacted).doesNotContain("hunter2", "Bearer abc", "/home/gahyeon")
                .contains("[REDACTED]", "[HOME]");
    }
}
