package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.core.speech.*;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.env.MapPropertySource;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class VoicePiperSelectionTest {
    @Test
    void explicitPiperSelectionRoutesEveryExpressionToStandardSpeech() {
        try (var context = new AnnotationConfigApplicationContext()) {
            context.getEnvironment().getPropertySources().addFirst(new MapPropertySource(
                    "piper-selection", Map.of("assistant.expressive-responses-enabled", "false")));
            context.register(VoiceAssistantExpressionPolicy.class);
            context.refresh();
            var policy = context.getBean(VoiceAssistantExpressionPolicy.class);
            var standard = mock(SpeechSynthesisUseCase.class);
            var expressive = mock(ExpressiveSpeechSynthesisUseCase.class);
            var router = new VoiceAssistantSpeechRouter(standard, expressive);
            for (String text : new String[]{"웃어봐", "고마워", "걱정돼", "영어 발음", "설명해줘"}) {
                var expression = policy.plan(text);
                assertThat(expression).isEqualTo(VoiceExpression.NATURAL);
                var segment = new SpeechSegment(0, text);
                router.synthesize(segment, VoiceProfileId.ASSISTANT, expression);
                verify(standard).synthesize(segment, VoiceProfileId.ASSISTANT);
            }
            verify(expressive, never()).synthesizeExpressive(any());
        }
    }
}
