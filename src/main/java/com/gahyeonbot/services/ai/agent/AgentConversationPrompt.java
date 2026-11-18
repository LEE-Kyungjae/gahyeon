package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.application.life.CharacterConversationContext;
import com.gahyeonbot.core.memory.MemoryRole;
import com.gahyeonbot.core.memory.MemorySnapshot;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;

import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 에이전트 실행의 첫 모델 입력(시스템 프롬프트, 공유 기억, 현재 질문, 백그라운드 결과)을 조립한다.
 */
final class AgentConversationPrompt {
    private final AgentPromptProvider promptProvider;

    AgentConversationPrompt(AgentPromptProvider promptProvider) {
        this.promptProvider = promptProvider;
    }

    List<Message> initialMessages(
            AgentRequest request,
            MemorySnapshot memory,
            String backgroundResult) {
        List<Message> messages = new ArrayList<>();
        messages.add(new SystemMessage(promptProvider.systemPrompt(memory.summary(), request.sessionKey())));
        if (usesSharedActorMemory(request.sessionKey())) {
            memory.recentMessages().forEach(message -> messages.add(
                    message.role() == MemoryRole.USER
                            ? new UserMessage(message.content())
                            : new AssistantMessage(message.content())));
        }
        messages.add(new UserMessage("""
                [modality]
                %s

                [응답 매체 지침]
                %s

                [현재 시각]
                %s

                [현재 질문]
                %s
                """.formatted(
                request.modality(),
                modalityGuidance(request.modality()),
                ZonedDateTime.now(ZoneId.of("Asia/Seoul")),
                request.message())));
        if (backgroundResult != null && !backgroundResult.isBlank()) {
            messages.add(new UserMessage("""
                    [백그라운드 작업 완료 결과]
                    %s

                    위 결과를 반영해 원래 요청에 대한 최종 답변을 작성해.
                    """.formatted(backgroundResult)));
        }
        return messages;
    }

    static String modalityGuidance(AgentModality modality) {
        return switch (modality) {
            case VOICE -> """
                    음성으로 듣기 편한 문장으로 답한다. 기본은 핵심부터 2~4문장으로 말하되,
                    사용자가 설명·비교·방법·논문 내용을 요구하면 이해에 필요한 만큼 충분히 설명한다.
                    기본 응답 언어는 한국어다. 사용자가 영어 또는 다른 언어로 답해 달라고 명시한 경우에만
                    해당 언어로 답하며, 영문 고유명사와 기술 용어는 원래 철자를 유지한다.
                    마크다운, 이모지, URL 낭독, 표, 장식용 특수문자는 사용하지 않는다.
                    """;
            case TEXT -> """
                    텍스트로 읽기 좋은 답변을 작성한다. 단순 질문은 짧게, 기술·논문·분석 질문은
                    결론과 근거가 빠지지 않도록 필요한 만큼 자세히 답한다. 길이를 캐릭터성 때문에 줄이지 않는다.
                    """;
            case SYSTEM -> "업무 목적과 전달 대상에 맞춰 간결성과 완전성을 조절한다.";
        };
    }

    static boolean usesSharedActorMemory(String sessionKey) {
        return CharacterConversationContext.fromScopedSessionKey(sessionKey).isEmpty();
    }
}
