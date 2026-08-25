package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class DefaultAgentRuntimeVoiceGuidanceTest {
    @Test
    void directVoiceActionsArePerformedBrieflyWithoutCapabilityDisclaimers() {
        String guidance = DefaultAgentRuntime.modalityGuidance(AgentModality.VOICE);

        assertThat(guidance).contains("한 문장");
        assertThat(guidance).contains("능력이 없다는 설명");
        assertThat(guidance).contains("직접 반응");
    }
}
