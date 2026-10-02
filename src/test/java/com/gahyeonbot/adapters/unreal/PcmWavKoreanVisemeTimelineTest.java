package com.gahyeonbot.adapters.unreal;

import com.gahyeonbot.core.speech.AudioOutput;
import org.junit.jupiter.api.Test;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import static org.assertj.core.api.Assertions.assertThat;

class PcmWavKoreanVisemeTimelineTest {
    @Test
    void derivesBoundedKoreanVowelTimelineFromActualPcmEnergy() {
        var aligner = new PcmWavKoreanVisemeTimeline();
        AudioOutput audio = wav(16_000, 1, 16_000, 0, 16_000);

        var cues = aligner.align("가 거 고 구 기", audio);

        assertThat(PcmWavKoreanVisemeTimeline.pcmWavDurationMs(audio)).isEqualTo(1_000);
        assertThat(cues).extracting(UnrealVisemeCue::semantic)
                .containsExactly("aa", "E", "O", "U", "I");
        assertThat(cues).isSortedAccordingTo(
                java.util.Comparator.comparingLong(UnrealVisemeCue::atMs));
        assertThat(cues).allSatisfy(cue -> {
            assertThat(cue.atMs()).isBetween(0L, 999L);
            assertThat(cue.durationMs()).isPositive();
            assertThat(cue.atMs() + cue.durationMs()).isLessThanOrEqualTo(1_000L);
            assertThat(cue.weight()).isBetween(0.35, 1.0);
        });
        assertThat(aligner.source()).isEqualTo("waveform-guided");
    }

    @Test
    void keepsMouthClosedDuringRealSilenceAndPlacesCuesInsideSpeechRegions() {
        var aligner = new PcmWavKoreanVisemeTimeline();
        AudioOutput audio = wav(16_000, 1, 16_000, 3_200, 6_400, 9_600, 12_800);

        var cues = aligner.align("가현이가 말해", audio);

        assertThat(cues).isNotEmpty();
        assertThat(cues).allSatisfy(cue -> assertThat(
                cue.atMs() >= 180 && cue.atMs() < 420
                        || cue.atMs() >= 580 && cue.atMs() < 820).isTrue());
        assertThat(aligner.align("가현", wav(16_000, 1, 16_000))).isEmpty();
    }

    @Test
    void rejectsUnsupportedOrMalformedAudioInsteadOfInventingTiming() {
        var aligner = new PcmWavKoreanVisemeTimeline();
        assertThat(aligner.align("가현", new AudioOutput(
                new byte[]{1, 2, 3}, "audio/mpeg", "mp3"))).isEmpty();
        assertThat(aligner.align("가현", new AudioOutput(
                new byte[44], "audio/wav", "wav"))).isEmpty();
    }

    @Test
    void capsTimelineAtProtocolLimit() {
        var aligner = new PcmWavKoreanVisemeTimeline();
        assertThat(aligner.align("가".repeat(1_000), wav(16_000, 1, 160_000, 0, 160_000)))
                .hasSize(256);
    }

    private static AudioOutput wav(int sampleRate, int channels, int frames, int... activeRanges) {
        int blockAlign = channels * 2;
        int dataBytes = frames * blockAlign;
        ByteBuffer bytes = ByteBuffer.allocate(44 + dataBytes).order(ByteOrder.LITTLE_ENDIAN);
        bytes.put("RIFF".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        bytes.putInt(36 + dataBytes);
        bytes.put("WAVEfmt ".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        bytes.putInt(16);
        bytes.putShort((short) 1);
        bytes.putShort((short) channels);
        bytes.putInt(sampleRate);
        bytes.putInt(sampleRate * blockAlign);
        bytes.putShort((short) blockAlign);
        bytes.putShort((short) 16);
        bytes.put("data".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        bytes.putInt(dataBytes);
        for (int frame = 0; frame < frames; frame++) {
            boolean active = false;
            for (int index = 0; index + 1 < activeRanges.length; index += 2) {
                if (frame >= activeRanges[index] && frame < activeRanges[index + 1]) active = true;
            }
            short sample = active ? (short) (Math.sin(frame * 0.11) * 12_000) : 0;
            for (int channel = 0; channel < channels; channel++) bytes.putShort(sample);
        }
        return new AudioOutput(bytes.array(), "audio/wav", "wav");
    }
}
