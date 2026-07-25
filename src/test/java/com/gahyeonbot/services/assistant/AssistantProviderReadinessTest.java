package com.gahyeonbot.services.assistant;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import com.gahyeonbot.services.ai.agent.AgentResult;
import com.gahyeonbot.services.ai.agent.AgentRuntime;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class AssistantProviderReadinessTest {
    @Test
    void providersStayDisabledWithoutKeys() {
        AssistantProperties properties = new AssistantProperties();
        properties.setEnabled(true);
        properties.getStt().setEnabled(true);
        properties.getOpenrouter().setEnabled(true);

        assertThat(new OpenAiTranscriptionProvider(properties, new ObjectMapper()).isReady()).isFalse();
        assertThat(new OpenRouterAssistantProvider(properties, runtimeStub()).isReady()).isFalse();
    }

    @Test
    void providersBecomeReadyOnlyWithExplicitConfiguration() {
        AssistantProperties properties = new AssistantProperties();
        properties.setEnabled(true);
        properties.getStt().setEnabled(true);
        properties.getStt().setApiKey("stt-key");
        properties.getOpenrouter().setEnabled(true);
        properties.getOpenrouter().setApiKey("openrouter-key");
        properties.getOpenrouter().setModel("provider/model");

        assertThat(new OpenAiTranscriptionProvider(properties, new ObjectMapper()).isReady()).isTrue();
        assertThat(new OpenRouterAssistantProvider(properties, runtimeStub()).isReady()).isTrue();
    }

    @Test
    void voiceGatewayUsesSharedAgentRuntimeAndGuildSession() {
        AssistantProperties properties = new AssistantProperties();
        properties.setEnabled(true);
        properties.getOpenrouter().setEnabled(true);
        properties.getOpenrouter().setApiKey("openrouter-key");
        properties.getOpenrouter().setModel("provider/model");
        CapturingRuntime runtime = new CapturingRuntime();

        String answer = new OpenRouterAssistantProvider(properties, runtime)
                .chat(10L, 20L, "tester", "날씨 알려줘");

        assertThat(answer).isEqualTo("응답");
        assertThat(runtime.request.gateway())
                .isEqualTo(com.gahyeonbot.services.ai.agent.AgentGateway.VOICE);
        assertThat(runtime.request.sessionKey()).isEqualTo("discord:voice:10");
        assertThat(runtime.request.userId()).isEqualTo(20L);
    }

    private static AgentRuntime runtimeStub() {
        return new AgentRuntime() {
            @Override public AgentResult execute(AgentRequest request) { return null; }
            @Override public AgentResult resume(String runId, long actorUserId) { return null; }
            @Override public AgentResult resumeBackground(String runId, String result) { return null; }
        };
    }

    private static final class CapturingRuntime implements AgentRuntime {
        private AgentRequest request;

        @Override
        public AgentResult execute(AgentRequest request) {
            this.request = request;
            return new AgentResult("run", "응답", List.of(), Duration.ofMillis(1));
        }

        @Override public AgentResult resume(String runId, long actorUserId) { return null; }
        @Override public AgentResult resumeBackground(String runId, String result) { return null; }
    }
}
