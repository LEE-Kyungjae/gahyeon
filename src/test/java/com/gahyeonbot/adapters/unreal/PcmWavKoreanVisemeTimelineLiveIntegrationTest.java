package com.gahyeonbot.adapters.unreal;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.speech.AudioOutput;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class PcmWavKoreanVisemeTimelineLiveIntegrationTest {
    @Test
    @EnabledIfEnvironmentVariable(named = "GAHYEON_VISEME_LIVE_WAV", matches = ".+")
    void derivesWaveformGuidedCuesFromARealGeneratedWav() throws Exception {
        Path path = Path.of(System.getenv("GAHYEON_VISEME_LIVE_WAV")).toAbsolutePath().normalize();
        String text = System.getenv().getOrDefault(
                "GAHYEON_VISEME_LIVE_TEXT", "잠깐만, 지금 확인해 볼게.");
        byte[] bytes = Files.readAllBytes(path);
        var aligner = new PcmWavKoreanVisemeTimeline();
        var audio = new AudioOutput(bytes, "audio/wav", "wav");

        var cues = aligner.align(text, audio);

        assertThat(cues).isNotEmpty().hasSizeLessThanOrEqualTo(256);
        assertThat(cues).isSortedAccordingTo(java.util.Comparator.comparingLong(UnrealVisemeCue::atMs));
        assertThat(cues).allSatisfy(cue -> {
            assertThat(cue.atMs() + cue.durationMs())
                    .isLessThanOrEqualTo(PcmWavKoreanVisemeTimeline.pcmWavDurationMs(audio));
            assertThat(cue.weight()).isBetween(0.35, 1.0);
        });
        System.out.println(new ObjectMapper().writeValueAsString(Map.of(
                "source", aligner.source(),
                "wav", path.toString(),
                "wavSha256", HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)),
                "audioDurationMs", PcmWavKoreanVisemeTimeline.pcmWavDurationMs(audio),
                "cueCount", cues.size(),
                "firstCueAtMs", cues.getFirst().atMs(),
                "lastCueAtMs", cues.getLast().atMs())));
    }
}
