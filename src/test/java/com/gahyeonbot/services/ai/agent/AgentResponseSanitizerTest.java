package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class AgentResponseSanitizerTest {

    @Test
    void keepsOnlyFinalAnswerAfterThinkingBlock() {
        assertThat(DefaultAgentRuntime.sanitizeFinalResponse(
                "내부 추론과 미완성 답변</think>실제로 사용자에게 보낼 답변"))
                .isEqualTo("실제로 사용자에게 보낼 답변");
    }

    @Test
    void removesPairedThinkingBlock() {
        assertThat(DefaultAgentRuntime.sanitizeFinalResponse(
                "<think>숨겨야 할 추론</think>\n근거가 확인된 답변"))
                .isEqualTo("근거가 확인된 답변");
    }
}
