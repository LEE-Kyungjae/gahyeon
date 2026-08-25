package com.gahyeonbot.services.ai.agent;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import com.gahyeonbot.application.life.CharacterConversationContext;
import com.gahyeonbot.application.life.CharacterDefinitionRegistry;
import com.gahyeonbot.application.life.CharacterMemoryStore;
import com.gahyeonbot.core.life.CharacterMemoryRecallPolicy;
import com.gahyeonbot.application.life.CharacterRelationshipStore;
import com.gahyeonbot.application.life.CharacterAutonomyWorkspaceService;
import com.gahyeonbot.application.knowledge.KnowledgeBaseService;

import java.nio.charset.StandardCharsets;

@Component
@Slf4j
public class AgentPromptProvider {
    private String systemPrompt;
    private CharacterDefinitionRegistry characters;
    private CharacterMemoryStore characterMemories;
    private CharacterRelationshipStore relationships;
    private CharacterAutonomyWorkspaceService workspace;
    private KnowledgeBaseService knowledge;

    @Autowired
    void configureCharacters(CharacterDefinitionRegistry characters, CharacterMemoryStore characterMemories) {
        this.characters = characters;
        this.characterMemories = characterMemories;
    }

    @Autowired
    void configureRelationships(CharacterRelationshipStore relationships) {
        this.relationships = relationships;
    }

    @Autowired(required = false)
    void configureWorkspace(CharacterAutonomyWorkspaceService workspace) {
        this.workspace = workspace;
    }

    @Autowired(required = false)
    void configureKnowledge(KnowledgeBaseService knowledge) {
        this.knowledge = knowledge;
    }

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

    public String systemPrompt(String longTermSummary, String sessionKey) {
        return systemPrompt(longTermSummary, sessionKey, null);
    }

    public String systemPrompt(String longTermSummary, String sessionKey, String currentQuery) {
        var context = CharacterConversationContext.fromScopedSessionKey(sessionKey);
        if (context.isEmpty() || characters == null || characterMemories == null) {
            return systemPrompt(longTermSummary);
        }
        var definition = characters.require(context.get().characterId());
        String persona = loadPrompt(definition.personaPrompt());
        String activeSoul = activeSoul(definition.id().value());
        String retrievedKnowledge = retrieveKnowledge(context.get().subjectId(), currentQuery);
        var recalled = new CharacterMemoryRecallPolicy().rank(
                characterMemories.recent(context.get().characterId(), context.get().worldId(),
                        context.get().subjectId(), 48), java.time.Instant.now(), 16);
        String memory = recalled.stream()
                .map(item -> "- [" + item.kind().name().toLowerCase() + "] " + item.content())
                .reduce((left, right) -> left + "\n" + right)
                .orElse("(없음)");
        String relationship = relationships == null || context.get().subjectId() == null
                ? "(초기 관계)"
                : relationships.find(context.get().characterId(), context.get().worldId(), context.get().subjectId())
                .map(state -> "familiarity=%.3f trust=%.3f affinity=%.3f tension=%.3f".formatted(
                        state.familiarity(), state.trust(), state.affinity(), state.tension()))
                .orElse("(초기 관계)");
        return persona + activeSoul + retrievedKnowledge + """

                [선택된 캐릭터]
                id=%s, name=%s

                [이 캐릭터만의 최근 기억]
                %s

                [현재 사용자와의 관계 상태]
                %s

                다른 캐릭터의 말투나 기억을 가져오지 않는다. 기억에 없는 사실을 아는 척하지 않는다.
                관계 상태는 말투의 친밀도와 조심성을 조절하는 참고값이며, 수치를 사용자에게 직접 읽지 않는다.
                """.formatted(definition.id().value(), definition.displayName(), memory, relationship);
    }

    private String retrieveKnowledge(String subjectId, String query) {
        if (knowledge == null || query == null || query.isBlank()) return "";
        try {
            var results = knowledge.search(new KnowledgeBaseService.SearchRequest("gahyeon", subjectId, query, 5));
            if (results.isEmpty()) return "";
            String evidence = results.stream()
                    .map(result -> "- source=%s title=%s score=%.3f\n  %s".formatted(
                            result.sourceId(), result.title(), result.score(), limited(result.content(), 1_200)))
                    .reduce((left, right) -> left + "\n" + right).orElse("");
            return "\n\n[권한 검증된 통합 지식 검색 결과]\n" + limited(evidence, 6_000)
                    + "\n검색 결과에 없는 사실은 지식베이스에 있다고 단정하지 않는다.";
        } catch (RuntimeException unavailable) {
            log.warn("통합 지식 검색 실패, 기존 프롬프트 유지", unavailable);
            return "";
        }
    }

    private String activeSoul(String characterId) {
        if (workspace == null) return "";
        try {
            return workspace.activeSoul(characterId)
                    .map(revision -> "\n\n[활성 Identity/Soul 리비전 %d]\n%s".formatted(
                            revision.revision(), limited(revision.soulMarkdown(), 12_000)))
                    .orElse("");
        } catch (RuntimeException unavailable) {
            log.warn("활성 캐릭터 Soul 조회 실패, 정적 persona 유지 characterId={}", characterId,
                    unavailable);
            return "";
        }
    }

    private static String limited(String value, int maximum) {
        return value.length() <= maximum ? value : value.substring(0, maximum) + "…";
    }

    private String loadPrompt(String location) {
        try {
            ClassPathResource resource = new ClassPathResource(location);
            return new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        } catch (Exception failure) {
            throw new IllegalStateException("캐릭터 인격 프롬프트 로드 실패: " + location, failure);
        }
    }
}
