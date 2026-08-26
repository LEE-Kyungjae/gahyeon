package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.core.speech.AudioOutput;
import com.gahyeonbot.core.speech.ExpressiveSpeechRequest;
import com.gahyeonbot.core.speech.ExpressiveSpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.SpeechSegment;
import com.gahyeonbot.core.speech.SpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.VoiceExpression;
import com.gahyeonbot.core.speech.VoiceProfileId;

final class VoiceAssistantSpeechRouter {
    private final SpeechSynthesisUseCase standard;
    private final ExpressiveSpeechSynthesisUseCase expressive;

    VoiceAssistantSpeechRouter(
            SpeechSynthesisUseCase standard,
            ExpressiveSpeechSynthesisUseCase expressive) {
        this.standard = standard;
        this.expressive = expressive;
    }

    AudioOutput synthesize(SpeechSegment segment, VoiceProfileId voice, VoiceExpression expression) {
        if (expressive != null && expressive.isExpressiveReady(voice)) {
            return expressive.synthesizeExpressive(new ExpressiveSpeechRequest(segment, voice, expression));
        }
        if (!VoiceExpression.NATURAL.equals(expression)) {
            throw new IllegalStateException("expressive TTS is required for style " + expression.style());
        }
        return standard.synthesize(segment, voice);
    }
}
