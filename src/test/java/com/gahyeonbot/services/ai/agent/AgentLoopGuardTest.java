package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AgentLoopGuardTest {
    @Test
    void identicalCallsAreStoppedAtConfiguredLimit() {
        AgentLoopGuard guard = new AgentLoopGuard(3);

        assertThatCode(() -> guard.recordToolCall("weather", "{}")).doesNotThrowAnyException();
        assertThatCode(() -> guard.recordToolCall("weather", "{}")).doesNotThrowAnyException();
        assertThatThrownBy(() -> guard.recordToolCall("weather", "{}"))
                .isInstanceOf(AgentLoopGuard.AgentLoopDetectedException.class)
                .hasMessageContaining("3회");
    }

    @Test
    void differentArgumentsDoNotCountAsSameLoop() {
        AgentLoopGuard guard = new AgentLoopGuard(3);

        assertThatCode(() -> {
            guard.recordToolCall("weather", "{\"city\":\"서울\"}");
            guard.recordToolCall("weather", "{\"city\":\"부산\"}");
            guard.recordToolCall("weather", "{\"city\":\"제주\"}");
        }).doesNotThrowAnyException();
    }
}
