package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.application.life.CharacterCatalogProperties;
import com.gahyeonbot.application.life.CharacterDefinitionRegistry;
import com.gahyeonbot.application.life.CharacterMemoryStore;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class GahyeonPersonalityRoutingTest {
    private static final String MARKER = "## 가현의 행동과 대화 예시 · 2026-10-03";

    private AgentPromptProvider provider() {
        var provider = new AgentPromptProvider();
        provider.load();
        provider.configureCharacters(
                new CharacterDefinitionRegistry(CharacterCatalogProperties.standard()),
                mock(CharacterMemoryStore.class));
        return provider;
    }

    @Test
    void legacyAndScopedConversationsReceiveTheSameApprovedPersonality() {
        var provider = provider();
        String legacy = provider.systemPrompt(null);
        String scoped = provider.systemPrompt(null,
                "character:gahyeon:gahyeon-home:actor:42|desktop:room-1");

        assertThat(legacy).contains(MARKER).doesNotContain("사용자와 오래 대화해 온");
        String personality = legacy.substring(legacy.indexOf(MARKER)).strip();
        assertThat(scoped).contains(personality);
        assertThat(legacy).contains("## 도구와 근거", "제공된 도구를 사용한다");
        assertThat(scoped).contains("[이 캐릭터만의 최근 기억]\n(없음)");
    }

    @Test
    void otherCharactersNeverInheritGahyeonsDialogueExamples() {
        var provider = provider();
        for (String id : new String[]{"diana", "ururu", "stella-lily"}) {
            String prompt = provider.systemPrompt(null,
                    "character:" + id + ":gahyeon-home:actor:42|desktop:room-1");
            assertThat(prompt).doesNotContain(MARKER, "저장 버튼이랑 또 엇갈렸네");
        }
    }

    @Test
    void exampleDialoguesAreSeparatedFromActualConversationMemory() {
        var provider = provider();
        String legacy = provider.systemPrompt("사용자는 재즈를 좋아한다.");
        assertThat(legacy).contains("서로 독립된 가상의 대화 예시", "현재 사용자의 실제 발언·기억·약속이 아니며")
                .endsWith("[사용자의 이전 대화 요약 - 참고 정보]\n사용자는 재즈를 좋아한다.");
        String scoped = provider.systemPrompt("사용자는 재즈를 좋아한다.",
                "character:gahyeon:gahyeon-home:actor:42|desktop:room-1");
        assertThat(scoped).doesNotContain("사용자는 재즈를 좋아한다.")
                .contains("[이 캐릭터만의 최근 기억]\n(없음)");
    }
}
