package com.gahyeonbot.services.tts;

import lombok.RequiredArgsConstructor;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class CustomVoiceTtsProvider implements TtsProvider {
    private final TtsProperties properties;

    @Override public String name() { return "custom"; }

    @Override
    public boolean isReady() {
        var custom = properties.getCustom();
        return properties.isEnabled() && hasText(custom.getEndpoint())
                && hasText(custom.getModel()) && hasText(custom.getSpeakerId());
    }

    @Override
    public Path synthesize(String text) throws Exception {
        if (!isReady()) throw new IllegalStateException("커스텀 음성 서버 설정이 필요합니다.");
        var custom = properties.getCustom();
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(custom.getTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(custom.getTimeoutSeconds()));
        RestTemplate client = new RestTemplate(factory);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(java.util.List.of(MediaType.valueOf(mediaType(custom.getFormat()))));
        if (hasText(custom.getApiKey())) headers.setBearerAuth(custom.getApiKey());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("text", text);
        body.put("model", custom.getModel());
        body.put("speakerId", custom.getSpeakerId());
        body.put("format", normalizedFormat(custom.getFormat()));

        ResponseEntity<byte[]> response = client.exchange(
                custom.getEndpoint(), HttpMethod.POST, new HttpEntity<>(body, headers), byte[].class);
        byte[] audio = response.getBody();
        if (audio == null || audio.length < 256) {
            throw new IllegalStateException("커스텀 음성 서버가 빈 오디오를 반환했습니다.");
        }

        Path dir = Path.of(System.getProperty("java.io.tmpdir"), "gahyeonbot-tts");
        Files.createDirectories(dir);
        Path path = Files.createTempFile(dir, "tts_custom_", "." + normalizedFormat(custom.getFormat()));
        try {
            Files.write(path, audio);
            return path;
        } catch (Exception e) {
            Files.deleteIfExists(path);
            throw e;
        }
    }

    private static String normalizedFormat(String format) {
        return "mp3".equalsIgnoreCase(format) ? "mp3" : "wav";
    }

    private static String mediaType(String format) {
        return "mp3".equalsIgnoreCase(format) ? "audio/mpeg" : "audio/wav";
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
