package com.gahyeonbot.services.tts;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class VoiceboxTtsProvider implements TtsProvider {
    private final TtsProperties properties;
    private final ObjectMapper objectMapper;

    @Override
    public String name() {
        return "voicebox";
    }

    @Override
    public boolean isReady() {
        var config = properties.getVoicebox();
        return properties.isEnabled()
                && hasText(config.getBaseUrl())
                && (hasText(config.getProfileId()) || hasText(config.getProfileName()));
    }

    @Override
    public Path synthesize(String text) throws Exception {
        if (!isReady()) {
            throw new IllegalStateException("Voicebox URL과 복제 음성 profile ID가 필요합니다.");
        }

        var config = properties.getVoicebox();
        RestTemplate client = client(config.getTimeoutSeconds());
        String baseUrl = stripTrailingSlash(config.getBaseUrl());

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("profile_id", resolveProfileId(client, baseUrl, config));
        request.put("text", text);
        request.put("language", config.getLanguage());
        request.put("engine", config.getEngine());
        request.put("model_size", config.getModelSize());
        request.put("normalize", config.isNormalize());

        HttpHeaders jsonHeaders = new HttpHeaders();
        jsonHeaders.setContentType(MediaType.APPLICATION_JSON);
        JsonNode generation = client.postForObject(
                baseUrl + "/generate",
                new HttpEntity<>(request, jsonHeaders),
                JsonNode.class);
        String generationId = generation == null ? null : generation.path("id").asText(null);
        if (!hasText(generationId)) {
            throw new IllegalStateException("Voicebox가 generation ID를 반환하지 않았습니다.");
        }

        waitUntilCompleted(client, baseUrl, generationId, config);

        ResponseEntity<byte[]> response = client.exchange(
                baseUrl + "/audio/" + generationId,
                HttpMethod.GET,
                HttpEntity.EMPTY,
                byte[].class);
        byte[] audio = response.getBody();
        if (audio == null || audio.length < 256) {
            throw new IllegalStateException("Voicebox가 빈 오디오를 반환했습니다.");
        }

        Path dir = Path.of(System.getProperty("java.io.tmpdir"), "gahyeonbot-tts");
        Files.createDirectories(dir);
        Path path = Files.createTempFile(dir, "tts_voicebox_", ".wav");
        try {
            Files.write(path, audio);
            return path;
        } catch (Exception e) {
            Files.deleteIfExists(path);
            throw e;
        }
    }

    private String resolveProfileId(
            RestTemplate client,
            String baseUrl,
            TtsProperties.Voicebox config) {
        if (hasText(config.getProfileId())) {
            return config.getProfileId();
        }

        JsonNode profiles = client.getForObject(baseUrl + "/profiles", JsonNode.class);
        if (profiles != null && profiles.isArray()) {
            for (JsonNode profile : profiles) {
                if (config.getProfileName().equals(profile.path("name").asText())) {
                    String id = profile.path("id").asText(null);
                    if (hasText(id)) {
                        return id;
                    }
                }
            }
        }
        throw new IllegalStateException(
                "Voicebox 프로필을 찾지 못했습니다: " + config.getProfileName());
    }

    private void waitUntilCompleted(
            RestTemplate client,
            String baseUrl,
            String generationId,
            TtsProperties.Voicebox config) throws Exception {
        long deadlineNanos = System.nanoTime()
                + Duration.ofSeconds(config.getTimeoutSeconds()).toNanos();
        long pollMillis = Math.max(100, config.getPollMillis());

        while (System.nanoTime() < deadlineNanos) {
            JsonNode status = client.getForObject(
                    baseUrl + "/history/" + generationId,
                    JsonNode.class);
            String state = status == null ? "" : status.path("status").asText("");
            if ("completed".equals(state)) {
                return;
            }
            if ("failed".equals(state)) {
                String error = status.path("error").asText("unknown error");
                throw new IllegalStateException("Voicebox 생성 실패: " + error);
            }
            Thread.sleep(pollMillis);
        }

        throw new IllegalStateException(
                "Voicebox 생성 시간이 " + config.getTimeoutSeconds() + "초를 초과했습니다.");
    }

    private static RestTemplate client(int timeoutSeconds) {
        int seconds = Math.max(1, timeoutSeconds);
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(Math.min(seconds, 10)));
        factory.setReadTimeout(Duration.ofSeconds(seconds));
        return new RestTemplate(factory);
    }

    private static String stripTrailingSlash(String value) {
        String result = value.trim();
        while (result.endsWith("/")) {
            result = result.substring(0, result.length() - 1);
        }
        return result;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
