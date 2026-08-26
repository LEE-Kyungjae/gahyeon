package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class DefaultAgentRuntimeVoiceGuidanceTest {
    @Test
    void defaultsVoiceAnswersToKoreanUnlessAnotherLanguageIsExplicitlyRequested() {
        String guidance = DefaultAgentRuntime.modalityGuidance(AgentModality.VOICE);

        assertThat(guidance).contains("기본 응답 언어는 한국어");
        assertThat(guidance).contains("명시한 경우에만");
        assertThat(guidance).contains("영문 고유명사와 기술 용어");
    }
}
