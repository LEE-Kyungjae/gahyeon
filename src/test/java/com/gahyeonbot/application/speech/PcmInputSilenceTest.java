package com.gahyeonbot.application.speech;

import org.junit.jupiter.api.Test;
import javax.sound.sampled.*;
import java.io.*;
import static org.assertj.core.api.Assertions.assertThat;

class PcmInputSilenceTest {
    @Test void detectsOneAndThreeSecondsOfExactSilence() throws Exception {
        assertThat(PcmInputSilence.isDigitalSilence(wav(new byte[32000], 16, 1))).isTrue();
        assertThat(PcmInputSilence.isDigitalSilence(wav(new byte[96000], 16, 1))).isTrue();
    }
    @Test void preservesEvenOneQuietNonzeroSample() throws Exception {
        byte[] samples = new byte[32000]; samples[16000] = 1;
        assertThat(PcmInputSilence.isDigitalSilence(wav(samples, 16, 1))).isFalse();
    }
    @Test void preservesSpeechInEitherStereoChannel() throws Exception {
        for (int index : new int[]{0, 2}) {
            byte[] samples = new byte[64000]; samples[index] = 1;
            assertThat(PcmInputSilence.isDigitalSilence(wav(samples, 16, 2))).isFalse();
        }
    }
    @Test void malformedAndEmptyAudioDoNotBecomeAcceptedSilence() throws Exception {
        assertThat(PcmInputSilence.isDigitalSilence(null)).isFalse();
        assertThat(PcmInputSilence.isDigitalSilence(new byte[32000])).isFalse();
        assertThat(PcmInputSilence.isDigitalSilence(wav(new byte[0], 16, 1))).isFalse();
        byte[] full = wav(new byte[32000], 16, 1);
        assertThat(PcmInputSilence.isDigitalSilence(java.util.Arrays.copyOf(full, full.length - 100))).isFalse();
    }
    @Test void unsupportedUnsignedPcmIsNotSuppressed() throws Exception {
        assertThat(PcmInputSilence.isDigitalSilence(wav(new byte[16000], 8, 1))).isFalse();
    }
    private static byte[] wav(byte[] pcm, int bits, int channels) throws Exception {
        var format = new AudioFormat(16000, bits, channels, bits == 16, false);
        var out = new ByteArrayOutputStream();
        try (var input = new AudioInputStream(new ByteArrayInputStream(pcm), format, pcm.length / format.getFrameSize())) {
            AudioSystem.write(input, AudioFileFormat.Type.WAVE, out);
        }
        return out.toByteArray();
    }
}
