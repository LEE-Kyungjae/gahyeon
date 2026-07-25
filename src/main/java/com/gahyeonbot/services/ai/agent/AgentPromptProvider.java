package com.gahyeonbot.services.ai.agent;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

@Component
@Slf4j
public class AgentPromptProvider {
    private String systemPrompt;

    @PostConstruct
    void load() {
        try {
            ClassPathResource resource = new ClassPathResource("prompts/gahyeon_system_prompt.txt");
            systemPrompt = new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            log.warn("에이전트 시스템 프롬프트 로드 실패, 기본 프롬프트 사용", e);
            systemPrompt = "너는 가현이야. 모르는 것은 추측하지 말고 도구 결과에 근거해 짧게 답해.";
        }
    }

    public String systemPrompt(String longTermSummary) {
        if (longTermSummary == null || longTermSummary.isBlank()) return systemPrompt;
        return systemPrompt + "\n\n[사용자의 이전 대화 요약 - 참고 정보]\n" + longTermSummary;
    }
}
