package com.gahyeonbot.application.speech;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Provider-neutral rejection policy for characteristic STT hallucinations. */
public final class TranscriptHallucinationPolicy {
    private TranscriptHallucinationPolicy() {}

    public static boolean rejects(String transcript, long capturedAudioMillis, long detectedSpeechMillis) {
        if (transcript == null || transcript.isBlank()) return false;
        String normalized = transcript.toLowerCase(Locale.ROOT)
                .replaceAll("[\\s\\p{Punct}]", "");
        boolean shortAudio = capturedAudioMillis <= 2_500 && detectedSpeechMillis <= 1_500;
        if (shortAudio && (normalized.equals("감사합니다")
                || normalized.equals("시청해주셔서감사합니다")
                || normalized.equals("자막제공")
                || normalized.equals("자막제공및광고를포함하고있습니다"))) {
            return true;
        }
        long meaningfulCharacters = transcript.codePoints()
                .filter(Character::isLetterOrDigit)
                .count();
        long plausibleCharacters = Math.max(12, (detectedSpeechMillis * 18 + 999) / 1_000);
        if (shortAudio && meaningfulCharacters > plausibleCharacters) return true;

        String[] tokens = transcript.toLowerCase(Locale.ROOT).split("[\\s\\p{Punct}]+");
        Map<String, Integer> frequencies = new HashMap<>();
        int tokenCount = 0;
        int largestFrequency = 0;
        for (String token : tokens) {
            String clean = token.replaceAll("[^\\p{L}\\p{N}]", "");
            if (clean.isBlank()) continue;
            tokenCount++;
            largestFrequency = Math.max(largestFrequency, frequencies.merge(clean, 1, Integer::sum));
        }
        return largestFrequency >= 3 && largestFrequency * 100 >= tokenCount * 60;
    }
}
