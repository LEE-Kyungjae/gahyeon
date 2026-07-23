package com.gahyeonbot.services.assistant;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
@RequiredArgsConstructor
public class OpenRouterAssistantProvider implements AssistantChatProvider {
    private static final String SYSTEM_PROMPT = """
            당신은 Discord 음성 채널의 한국어 업무 비서 가현이다.
            답변은 음성으로 읽기 좋게 짧고 명확하게 한다.
            실제 외부 작업을 수행했다고 거짓말하지 말고, 권한이 없는 일정 등록이나 메시지 전송은 초안으로 제안한다.
            회의에서는 결정사항, 담당자, 기한을 구분한다.
            """;

    private final AssistantProperties properties;
    private final ObjectMapper objectMapper;
    private final Map<String, List<Map<String, String>>> conversations = new ConcurrentHashMap<>();

    @Override
    public boolean isReady() {
        var p = properties.getOpenrouter();
        return properties.isEnabled() && p.isEnabled()
                && hasText(p.getApiKey()) && hasText(p.getModel());
    }

    @Override
    public String chat(long guildId, long userId, String username, String message) {
        if (!isReady()) throw new IllegalStateException("OpenRouter가 설정되지 않았습니다.");
        var p = properties.getOpenrouter();
        // Everyone in one guild assistant session shares meeting context.
        String key = Long.toString(guildId);
        List<Map<String, String>> history = conversations.computeIfAbsent(
                key, ignored -> new java.util.concurrent.CopyOnWriteArrayList<>());
        history.add(Map.of("role", "user", "content", username + ": " + message));
        while (history.size() > 12) history.remove(0);

        var messages = new java.util.ArrayList<Map<String, String>>();
        messages.add(Map.of("role", "system", "content", SYSTEM_PROMPT));
        messages.addAll(history);

        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(p.getTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(p.getTimeoutSeconds()));
        RestTemplate client = new RestTemplate(factory);
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(p.getApiKey());
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(List.of(MediaType.TEXT_EVENT_STREAM));
        headers.set("HTTP-Referer", "https://github.com/LEE-Kyungjae/gahyeonbot");
        headers.set("X-OpenRouter-Title", "GahyeonBot Voice Assistant");

        Map<String, Object> body = Map.of(
                "model", p.getModel(),
                "messages", messages,
                "stream", true,
                "stream_options", Map.of("include_usage", true));
        try {
            String requestJson = objectMapper.writeValueAsString(body);
            String answer = client.execute(
                    trimSlash(p.getBaseUrl()) + "/chat/completions",
                    HttpMethod.POST,
                    request -> {
                        request.getHeaders().putAll(headers);
                        request.getBody().write(requestJson.getBytes(StandardCharsets.UTF_8));
                    },
                    response -> {
                        if (!response.getStatusCode().is2xxSuccessful()) {
                            String error = new String(response.getBody().readAllBytes(), StandardCharsets.UTF_8);
                            throw new IllegalStateException("OpenRouter HTTP "
                                    + response.getStatusCode().value() + ": " + error);
                        }
                        StringBuilder result = new StringBuilder();
                        try (BufferedReader reader = new BufferedReader(
                                new InputStreamReader(response.getBody(), StandardCharsets.UTF_8))) {
                            String line;
                            while ((line = reader.readLine()) != null) {
                                if (!line.startsWith("data:")) continue; // includes SSE keep-alive comments
                                String data = line.substring(5).trim();
                                if (data.isEmpty() || "[DONE]".equals(data)) continue;
                                JsonNode event = objectMapper.readTree(data);
                                if (event.has("error")) {
                                    throw new IllegalStateException(
                                            "OpenRouter 스트림 오류: " + event.path("error").toString());
                                }
                                JsonNode content = event.path("choices").path(0).path("delta").path("content");
                                if (content.isTextual()) result.append(content.asText());
                            }
                        }
                        return result.toString();
                    });
            answer = answer == null ? "" : answer.trim();
            if (answer.isEmpty()) throw new IllegalStateException("OpenRouter 응답이 비어 있습니다.");
            history.add(Map.of("role", "assistant", "content", answer));
            return answer;
        } catch (Exception e) {
            throw new IllegalStateException("OpenRouter 응답을 해석하지 못했습니다.", e);
        }
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static String trimSlash(String value) {
        return value != null && value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }
}
