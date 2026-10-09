package com.gahyeonbot.adapters.speech;

import com.gahyeonbot.application.speech.VoiceActivityDetector;
import java.util.Locale;

/** Explicit selection; configuration or model errors must never silently disable VAD. */
public final class VoiceActivityDetectorFactory {
    private VoiceActivityDetectorFactory() {}

    public static VoiceActivityDetector create(String provider, int hopSize, float threshold, String modelPath) {
        if (provider == null || provider.isBlank()) throw new IllegalArgumentException("VAD provider is required");
        return switch (provider.toLowerCase(Locale.ROOT)) {
            case "ten" -> new TenVadDetector(hopSize, threshold);
            case "silero" -> new SileroVadDetector(threshold, modelPath);
            default -> throw new IllegalArgumentException("Unknown VAD provider: " + provider);
        };
    }
}
