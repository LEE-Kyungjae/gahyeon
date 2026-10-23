package com.gahyeonbot.adapters.speech;

import org.junit.jupiter.api.Test;
import java.util.Arrays;
import static org.assertj.core.api.Assertions.*;

class SileroVadDetectorTest {
    @Test void exactSilenceNeverBecomesSpeechAcrossLongStream() {
        try (var detector = new SileroVadDetector(.5f, "")) {
            for (int i = 0; i < 1500; i++) {
                assertThat(detector.detect(new byte[3840]).voiceSamples()).isZero();
            }
        }
    }

    @Test void partialWindowsAreRetainedAcrossPacketBoundaries() {
        byte[] signal = new byte[48000 * 4];
        new java.util.Random(71).nextBytes(signal);
        try (var whole = new SileroVadDetector(.3f, "");
             var split = new SileroVadDetector(.3f, "")) {
            long expected = whole.detect(signal).voiceSamples();
            long actual = 0;
            for (int offset = 0; offset < signal.length; offset += 388) {
                actual += split.detect(Arrays.copyOfRange(signal, offset,
                        Math.min(offset + 388, signal.length))).voiceSamples();
            }
            assertThat(actual).isEqualTo(expected);
        }
    }

    @Test void closingOneUserDoesNotCloseAnotherUsersModel() {
        var first = new SileroVadDetector(.5f, "");
        try (var second = new SileroVadDetector(.5f, "")) {
            first.close();
            first.close();
            assertThat(second.detect(new byte[3840]).voice()).isFalse();
            assertThatThrownBy(() -> first.detect(new byte[3840])).isInstanceOf(IllegalStateException.class);
        }
    }

    @Test void invalidModelAndThresholdFailInsteadOfDisablingVad() {
        assertThatThrownBy(() -> new SileroVadDetector(.5f, "/missing/silero.onnx"))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new SileroVadDetector(Float.NaN, ""))
                .isInstanceOf(IllegalArgumentException.class);
        try (var detector = new SileroVadDetector(.5f, "")) {
            assertThatThrownBy(() -> detector.detect(new byte[3])).isInstanceOf(IllegalArgumentException.class);
        }
    }
}
