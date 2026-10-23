package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.core.speech.*;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.ResourceAccessException;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.any;

/** Reproduces the unresolved 2026-10-03 incident; passing is not a fix claim. */
class VoiceIncidentCharacterizationTest {
    @Test
    void configuredProgressSpeechIsAdmittedWithoutToolExecutionEvidence() {
        var settings = new AssistantProperties();
        var policy = new VoiceAcknowledgementPolicy();
        try (var first = policy.tryAcquire(0, 30_000, "", settings.getResponseAcknowledgementTexts()).orElseThrow()) {
            assertThat(first.message()).contains("정리해서");
        }
        try (var second = policy.tryAcquire(30_000, 30_000, "", settings.getResponseAcknowledgementTexts()).orElseThrow()) {
            assertThat(second.message()).contains("알아보고");
        }
    }

    @Test
    void expressiveConnectionFailurePropagatesWithoutStandardAudioFallback() {
        var standard = mock(SpeechSynthesisUseCase.class);
        var expressive = mock(ExpressiveSpeechSynthesisUseCase.class);
        when(expressive.isExpressiveReady(VoiceProfileId.ASSISTANT)).thenReturn(true);
        when(expressive.synthesizeExpressive(any())).thenThrow(new ResourceAccessException("Connection refused"));
        var router = new VoiceAssistantSpeechRouter(standard, expressive);
        assertThatThrownBy(() -> router.synthesize(new SpeechSegment(0, "설명 본문"),
                VoiceProfileId.ASSISTANT, VoiceExpression.NATURAL))
                .isInstanceOf(ResourceAccessException.class);
        verify(standard, never()).synthesize(any(), any());
    }
}
