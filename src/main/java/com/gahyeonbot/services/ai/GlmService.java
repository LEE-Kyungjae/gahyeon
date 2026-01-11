package com.gahyeonbot.services.ai;

import com.gahyeonbot.config.AppCredentialsConfig;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

/**
 * Zhipu AI GLM-4-flash API 서비스.
 * 대화 요약 전용으로 사용됩니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GlmService {

    private static final String GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions";
    private static final String GLM_MODEL = "glm-4-flash";
    private static final int MAX_TOKENS = 150;

    private final AppCredentialsConfig appCredentialsConfig;

    private String apiKey;
    private boolean isEnabled = false;
    private RestTemplate restTemplate;

    @PostConstruct
    public void initialize() {
        this.apiKey = appCredentialsConfig.getGlmApiKey();

        if (apiKey == null || apiKey.isEmpty() || apiKey.startsWith("your_")) {
            log.warn("GLM_API_KEY가 설정되지 않았습니다. 대화 요약 기능이 비활성화됩니다.");
            this.isEnabled = false;
            return;
        }

        try {
            this.restTemplate = new RestTemplate();
            this.isEnabled = true;
            log.info("GLM 서비스가 활성화되었습니다. 모델: {}", GLM_MODEL);
        } catch (Exception e) {
            log.error("GLM 초기화 실패. 대화 요약 기능이 비활성화됩니다.", e);
            this.isEnabled = false;
        }
    }

    /**
     * 대화 내용을 요약합니다.
     *
     * @param userMessage 사용자 메시지
     * @param aiResponse AI 응답
     * @return 요약된 대화 (한 문장)
     */
    public String summarize(String userMessage, String aiResponse) {
        if (!isEnabled) {
            log.debug("GLM 서비스 비활성화 상태, 간단 요약 사용");
            return simpleSummary(userMessage, aiResponse);
        }

        try {
            String prompt = String.format(
                    "다음 대화를 핵심만 담아 한 문장(50자 이내)으로 요약해줘. 불필요한 표현 없이 내용만:\n\n사용자: %s\nAI: %s",
                    truncate(userMessage, 200),
                    truncate(aiResponse, 300)
            );

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            Map<String, Object> requestBody = Map.of(
                    "model", GLM_MODEL,
                    "messages", List.of(
                            Map.of("role", "user", "content", prompt)
                    ),
                    "max_tokens", MAX_TOKENS,
                    "temperature", 0.3
            );

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);

            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    GLM_API_URL,
                    HttpMethod.POST,
                    request,
                    new ParameterizedTypeReference<>() {}
            );

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return extractContent(response.getBody());
            }

            log.warn("GLM API 응답 실패, 간단 요약 사용");
            return simpleSummary(userMessage, aiResponse);

        } catch (Exception e) {
            log.error("GLM 요약 실패: {}", e.getMessage());
            return simpleSummary(userMessage, aiResponse);
        }
    }

    /**
     * GLM API 응답에서 content 추출
     */
    @SuppressWarnings("unchecked")
    private String extractContent(Map<String, Object> responseBody) {
        try {
            List<Map<String, Object>> choices = (List<Map<String, Object>>) responseBody.get("choices");
            if (choices != null && !choices.isEmpty()) {
                Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
                if (message != null) {
                    String content = (String) message.get("content");
                    if (content != null && !content.trim().isEmpty()) {
                        return content.trim();
                    }
                }
            }
        } catch (Exception e) {
            log.error("GLM 응답 파싱 실패", e);
        }
        return null;
    }

    /**
     * 간단 요약 (GLM 실패 시 폴백)
     */
    private String simpleSummary(String userMessage, String aiResponse) {
        String q = truncate(userMessage, 30);
        String a = truncate(aiResponse, 30);
        return String.format("Q: %s / A: %s", q, a);
    }

    /**
     * 문자열 자르기
     */
    private String truncate(String text, int maxLength) {
        if (text == null) return "";
        text = text.replaceAll("\\s+", " ").trim();
        if (text.length() <= maxLength) return text;
        return text.substring(0, maxLength) + "...";
    }

    /**
     * 서비스 활성화 상태 확인
     */
    public boolean isEnabled() {
        return isEnabled;
    }
}
