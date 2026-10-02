package com.gahyeonbot.adapters.unreal;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.speech.AudioOutput;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;

import static org.assertj.core.api.Assertions.assertThat;

/** Exports the exact Core fallback timeline consumed by the UE live visual proof. */
class PcmWavVisemeFixtureExportTest {
    @Test
    @EnabledIfEnvironmentVariable(named = "GAHYEON_VISEME_FIXTURE_OUTPUT", matches = ".+")
    void exportsExactWaveformGuidedTimeline() throws Exception {
        Path wav = Path.of(System.getenv("GAHYEON_VISEME_LIVE_WAV"))
                .toAbsolutePath().normalize();
        Path output = Path.of(System.getenv("GAHYEON_VISEME_FIXTURE_OUTPUT"))
                .toAbsolutePath().normalize();
        String text = System.getenv().getOrDefault(
                "GAHYEON_VISEME_LIVE_TEXT", "잠깐만, 지금 확인해 볼게.");
        byte[] bytes = Files.readAllBytes(wav);
        var aligner = new PcmWavKoreanVisemeTimeline();
        var cues = aligner.align(text, new AudioOutput(bytes, "audio/wav", "wav"));
        assertThat(cues).isNotEmpty();

        var payload = new LinkedHashMap<String, Object>();
        payload.put("schemaVersion", 1);
        payload.put("source", aligner.source());
        payload.put("text", text);
        payload.put("audioDurationMs", PcmWavKoreanVisemeTimeline.pcmWavDurationMs(
                new AudioOutput(bytes, "audio/wav", "wav")));
        payload.put("visemes", cues);
        Files.createDirectories(output.getParent());
        new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(output.toFile(), payload);
        assertThat(Files.size(output)).isPositive();
    }
}
