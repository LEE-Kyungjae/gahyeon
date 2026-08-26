package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.core.speech.ExpressiveSpeechRequest;
import com.gahyeonbot.core.speech.ExpressiveSpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.SpeechSegment;
import com.gahyeonbot.core.speech.SpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.VoiceExpression;
import com.gahyeonbot.core.speech.VoiceProfileId;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class VoiceAssistantSpeechRouterTest {
    private final SpeechSynthesisUseCase standard = mock(SpeechSynthesisUseCase.class);
    private final ExpressiveSpeechSynthesisUseCase expressive = mock(ExpressiveSpeechSynthesisUseCase.class);
    private final SpeechSegment segment = new SpeechSegment(0, "하하, 좋아.");

    @Test
    void routesLaughterThroughTheAttestedExpressiveProvider() {
        when(expressive.isExpressiveReady(VoiceProfileId.ASSISTANT)).thenReturn(true);
        var router = new VoiceAssistantSpeechRouter(standard, expressive);
        var expression = new VoiceExpression("suppressed_laugh", 0.72, "respond_with_audible_laughter");

        router.synthesize(segment, VoiceProfileId.ASSISTANT, expression);

        verify(expressive).synthesizeExpressive(new ExpressiveSpeechRequest(
                segment, VoiceProfileId.ASSISTANT, expression));
        verify(standard, never()).synthesize(any(), any());
    }

    @Test
    void routesNaturalSpeechThroughTheExpressiveProviderWhenItIsReady() {
        when(expressive.isExpressiveReady(VoiceProfileId.ASSISTANT)).thenReturn(true);
        var router = new VoiceAssistantSpeechRouter(standard, expressive);

        router.synthesize(segment, VoiceProfileId.ASSISTANT, VoiceExpression.NATURAL);

        verify(expressive).synthesizeExpressive(new ExpressiveSpeechRequest(
                segment, VoiceProfileId.ASSISTANT, VoiceExpression.NATURAL));
        verify(standard, never()).synthesize(any(), any());
    }

    @Test
    void fallsBackToStandardOnlyForNaturalSpeechWhenExpressiveIsUnavailable() {
        var router = new VoiceAssistantSpeechRouter(standard, expressive);

        router.synthesize(segment, VoiceProfileId.ASSISTANT, VoiceExpression.NATURAL);

        verify(standard).synthesize(segment, VoiceProfileId.ASSISTANT);
        verify(expressive, never()).synthesizeExpressive(any());
    }

    @Test
    void failsClosedInsteadOfFlatteningLaughterToNeutralSpeech() {
        var router = new VoiceAssistantSpeechRouter(standard, expressive);
        var expression = new VoiceExpression("suppressed_laugh", 0.72, "respond_with_audible_laughter");

        assertThatThrownBy(() -> router.synthesize(segment, VoiceProfileId.ASSISTANT, expression))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("expressive TTS is required");
        verify(standard, never()).synthesize(any(), any());
    }
}
