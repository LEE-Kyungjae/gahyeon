package com.gahyeonbot.services.assistant;

import com.gahyeonbot.services.ai.agent.AgentGateway;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import com.gahyeonbot.services.ai.agent.AgentResult;
import com.gahyeonbot.services.ai.agent.AgentRuntime;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.UUID;

/**
 * Discord 음성 채널을 공통 에이전트 런타임에 연결하는 게이트웨이.
 *
 * 이름은 기존 설정과 호환하기 위해 유지하지만, 대화 상태와 도구 실행은
 * 텍스트 명령과 동일한 AgentRuntime이 담당한다.
 */
@Service
@RequiredArgsConstructor
public class OpenRouterAssistantProvider implements AssistantChatProvider {
    private final AssistantProperties properties;
    private final AgentRuntime agentRuntime;

    @Override
    public boolean isReady() {
        var p = properties.getOpenrouter();
        return properties.isEnabled() && p.isEnabled()
                && hasText(p.getApiKey()) && hasText(p.getModel());
    }

    @Override
    public String chat(long guildId, long userId, String username, String message) {
        if (!isReady()) {
            throw new IllegalStateException("OpenRouter 에이전트가 설정되지 않았습니다.");
        }
        AgentResult result = agentRuntime.execute(new AgentRequest(
                "voice:" + guildId + ":" + UUID.randomUUID(),
                "discord:voice:" + guildId,
                AgentGateway.VOICE,
                guildId,
                userId,
                username,
                message,
                8));
        return result.content();
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
