package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.core.speech.VoiceExpression;
import org.springframework.stereotype.Component;

import java.util.Locale;

@Component
final class VoiceAssistantExpressionPolicy {
    VoiceExpression plan(String transcript) {
        String normalized = transcript == null ? "" : transcript.trim().toLowerCase(Locale.ROOT);
        if (containsAny(normalized, "웃어", "웃음", "ㅋㅋ", "ㅎㅎ")) {
            return new VoiceExpression("suppressed_laugh", 0.72, "respond_with_audible_laughter");
        }
        if (containsAny(normalized, "고마워", "감사")) {
            return new VoiceExpression("warm", 0.46, "acknowledge_gratitude_briefly");
        }
        if (containsAny(normalized, "걱정", "불안", "괜찮아?", "괜찮나요", "무서워")) {
            return new VoiceExpression("concerned", 0.38, "respond_with_attentive_concern");
        }
        if (containsAny(normalized, "영어", "영문", "english", "발음")) {
            return new VoiceExpression("natural", 0.34, "speak_with_clear_english_pronunciation");
        }
        return VoiceExpression.NATURAL;
    }

    private static boolean containsAny(String text, String... candidates) {
        for (String candidate : candidates) if (text.contains(candidate)) return true;
        return false;
    }
}
