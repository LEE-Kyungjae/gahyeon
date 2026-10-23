package com.gahyeonbot.adapters.speech;

import com.gahyeonbot.application.speech.*;
import org.junit.jupiter.api.Test;
import javax.sound.sampled.AudioSystem;
import java.io.ByteArrayInputStream;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

class SileroVadAdmissionTest {
    @Test void nonSpeechDoesNotReachTranscriptionWithShortReplyCandidateSettings() {
        for (String kind : List.of("silence", "quiet-noise", "loud-noise", "hum", "clicks", "tone", "fan")) {
            var random = new Random(20261009);
            byte[] pcm = new byte[8 * 192000];
            double low = 0;
            for (int i = 0; i < pcm.length / 4; i++) {
                double white = random.nextGaussian();
                low = .995 * low + .005 * white;
                double value = switch (kind) {
                    case "quiet-noise" -> white * 25;
                    case "loud-noise" -> white * 2000;
                    case "hum" -> 700 * Math.sin(2 * Math.PI * 60 * i / 48000);
                    case "clicks" -> 12000 * Math.exp(-(i % 24000) / 120.0) * white;
                    case "tone" -> 3000 * Math.sin(2 * Math.PI * 1000 * i / 48000);
                    case "fan" -> low * 10000 + white * 100;
                    default -> 0;
                };
                short sample = (short) Math.max(-32768, Math.min(32767, Math.round(value)));
                for (int channel = 0; channel < 2; channel++) {
                    pcm[i * 4 + channel * 2] = (byte) sample;
                    pcm[i * 4 + channel * 2 + 1] = (byte) (sample >> 8);
                }
            }
            assertThat(admitted(pcm)).as(kind).isZero();
        }
    }

    @Test void preservesQuietKoreanYesWithTheSameSettings() throws Exception {
        byte[] wav;
        try (var resource = getClass().getResourceAsStream("/voice/vad/synthetic-ko-yes.wav")) {
            wav = resource.readAllBytes();
        }
        byte[] speech;
        try (var audio = AudioSystem.getAudioInputStream(new ByteArrayInputStream(wav))) {
            speech = audio.readAllBytes();
        }
        for (double gain : new double[]{1, .08}) {
            byte[] pcm = new byte[192000 * 4 + speech.length];
            for (int i = 0; i < speech.length; i += 2) {
                short sample = (short) ((speech[i] & 255) | (speech[i + 1] << 8));
                short quiet = (short) Math.round(sample * gain);
                pcm[192000 + i] = (byte) quiet;
                pcm[192000 + i + 1] = (byte) (quiet >> 8);
            }
            assertThat(admitted(pcm)).as("gain=%s", gain).isEqualTo(1);
        }
    }

    private int admitted(byte[] pcm) {
        var policy = new UtteranceSegmentationPolicy(192000, 20, 96000,
                1500, 150, 1000, 2000, 700, 16000);
        int count = 0;
        long nextPoll = 250;
        try (var accumulator = new StreamingUtteranceAccumulator(policy,
                new SileroVadDetector(.3f, ""), 0)) {
            for (int offset = 0; offset < pcm.length; offset += 3840) {
                long now = offset / 192;
                accumulator.accept(Arrays.copyOfRange(pcm, offset, Math.min(offset + 3840, pcm.length)), now);
                if (now >= nextPoll) {
                    nextPoll += 250;
                    if (accumulator.poll(now).isPresent()) count++;
                }
            }
            if (accumulator.poll(pcm.length / 192 + 3000).isPresent()) count++;
        }
        return count;
    }
}
