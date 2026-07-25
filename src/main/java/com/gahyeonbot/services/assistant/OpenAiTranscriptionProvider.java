package com.gahyeonbot.services.assistant;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

@Service
@RequiredArgsConstructor
@Slf4j
public class OpenAiTranscriptionProvider implements SpeechToTextProvider {
    private final AssistantProperties properties;
    private final ObjectMapper objectMapper;

    @Override
    public boolean isReady() {
        var p = properties.getStt();
        return properties.isEnabled() && p.isEnabled()
                && (!p.isApiKeyRequired() || hasText(p.getApiKey()))
                && hasText(p.getModel());
    }

    @Override
    public String transcribe(byte[] wavAudio) {
        if (!isReady()) throw new IllegalStateException("STT가 설정되지 않았습니다.");

        var p = properties.getStt();
        try {
            return request(wavAudio, p.getBaseUrl(), p.getEndpoint(), p.getModel(), p.getPrompt());
        } catch (RuntimeException primaryFailure) {
            if (!hasText(p.getFallbackBaseUrl())) throw primaryFailure;
            log.warn("주 STT 호출 실패, fallback STT로 전환합니다: {}", primaryFailure.getMessage());
            return request(wavAudio, p.getFallbackBaseUrl(), p.getFallbackEndpoint(),
                    p.getFallbackModel(), "");
        }
    }

    private String request(
            byte[] wavAudio,
            String baseUrl,
            String endpoint,
            String model,
            String prompt) {
        var p = properties.getStt();
        var requestFactory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(p.getTimeoutSeconds()));
        requestFactory.setReadTimeout(Duration.ofSeconds(p.getTimeoutSeconds()));
        RestTemplate client = new RestTemplate(requestFactory);

        HttpHeaders headers = new HttpHeaders();
        if (hasText(p.getApiKey())) headers.setBearerAuth(p.getApiKey());
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(wavAudio) {
            @Override public String getFilename() { return "utterance.wav"; }
        });
        body.add("model", model);
        body.add("response_format", "json");
        if (hasText(p.getLanguage())) body.add("language", p.getLanguage());
        if (hasText(prompt)) body.add("prompt", prompt);

        ResponseEntity<String> response = client.exchange(
                trimSlash(baseUrl) + normalizedEndpoint(endpoint),
                HttpMethod.POST, new HttpEntity<>(body, headers), String.class);
        try {
            JsonNode json = objectMapper.readTree(response.getBody());
            return json.path("text").asText("").trim();
        } catch (Exception e) {
            throw new IllegalStateException("STT 응답을 해석하지 못했습니다.", e);
        }
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static String trimSlash(String value) {
        return value != null && value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }

    private static String normalizedEndpoint(String endpoint) {
        return endpoint != null && endpoint.startsWith("/") ? endpoint : "/" + endpoint;
    }
}
