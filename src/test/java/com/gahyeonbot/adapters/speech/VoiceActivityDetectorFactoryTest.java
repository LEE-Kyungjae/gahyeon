package com.gahyeonbot.adapters.speech;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class VoiceActivityDetectorFactoryTest {
    @Test void selectsSileroAndRejectsUnknownProviders() {
        try (var detector = VoiceActivityDetectorFactory.create("silero", 256, .5f, "")) {
            assertThat(detector).isInstanceOf(SileroVadDetector.class);
            assertThat(detector.detect(new byte[6144]).voice()).isFalse();
        }
        assertThatThrownBy(() -> VoiceActivityDetectorFactory.create("sillero", 256, .5f, ""))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VoiceActivityDetectorFactory.create(null, 256, .5f, ""))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
