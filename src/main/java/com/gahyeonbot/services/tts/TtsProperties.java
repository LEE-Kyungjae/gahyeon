package com.gahyeonbot.services.tts;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * TTS 설정.
 * - Piper + (optional) KSS sentence splitting via python script.
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

    private final Piper piper = new Piper();
    private final Kss kss = new Kss();

    @Getter
    @Setter
    public static class Piper {
        /**
         * Piper model spec.
         * - If ends with ".onnx" (or an existing file path): treated as local model path.
         * - Else: treated as a piper-tts voice name (e.g., "ko_KR-kss-medium") and will use --data-dir.
         */
        private String model = "ko_KR-kss-medium";

        /** Optional local config path for a local .onnx model (voice.json). */
        private String config;

        /** Piper data dir for voice downloads (used when model is a voice name). */
        private String dataDir = "/app/piper_data";

        /** Piper executable (from piper-tts). */
        private String bin = "piper";
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

