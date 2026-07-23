package com.gahyeonbot.services.tts;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class TtsServiceProviderTest {
    @Test
    void usesSelectedCustomProvider() throws Exception {
        TtsProperties properties = new TtsProperties();
        properties.setProvider("custom");
        Path customAudio = Path.of("custom.wav");
        TtsService service = new TtsService(properties, new ObjectMapper(), List.of(
                provider("custom", true, customAudio, null),
                provider("edge", true, Path.of("edge.mp3"), null)));

        assertThat(service.synthesizeSegmentToAudio("안녕")).isEqualTo(customAudio);
    }

    @Test
    void fallsBackToEdgeWhenCustomFails() throws Exception {
        TtsProperties properties = new TtsProperties();
        properties.setProvider("custom");
        properties.setFallbackToEdge(true);
        Path edgeAudio = Path.of("edge.mp3");
        TtsService service = new TtsService(properties, new ObjectMapper(), List.of(
                provider("custom", true, null, new IllegalStateException("offline")),
                provider("edge", true, edgeAudio, null)));

        assertThat(service.synthesizeSegmentToAudio("안녕")).isEqualTo(edgeAudio);
    }

    private static TtsProvider provider(String name, boolean ready, Path result, Exception failure) {
        return new TtsProvider() {
            @Override public String name() { return name; }
            @Override public boolean isReady() { return ready; }
            @Override public Path synthesize(String text) throws Exception {
                if (failure != null) throw failure;
                return result;
            }
        };
    }
}
