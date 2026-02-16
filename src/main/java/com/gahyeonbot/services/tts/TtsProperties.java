package com.gahyeonbot.services.tts;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * TTS 설정.
 * - Edge TTS + (optional) KSS sentence splitting via python script.
 */
@Component
@ConfigurationProperties(prefix = "tts")
@Getter
@Setter
public class TtsProperties {
    private boolean enabled = true;

    /** Max input chars for a single /tts request. */
    private int maxChars = 400;

    /** Soft cap per segment before we chunk further. */
    private int segmentMaxChars = 120;

    /** Process timeout for splitter + synthesis. */
    private int timeoutSeconds = 20;

    private final Edge edge = new Edge();
    private final Kss kss = new Kss();

    @Getter
    @Setter
    public static class Edge {
        /** edge-tts executable. */
        private String bin = "edge-tts";

        /** Korean female neural voice. */
        private String voice = "ko-KR-SunHiNeural";

        /** Speech rate, e.g. +0%, -10%. */
        private String rate = "+0%";

        /** Speech pitch, e.g. +0Hz, -20Hz. */
        private String pitch = "+0Hz";
    }

    @Getter
    @Setter
    public static class Kss {
        /** Python executable. */
        private String python = "python3";

        /** Splitter script path (copied into image as /app/tts_split.py). */
        private String script = "/app/tts_split.py";
    }
}
