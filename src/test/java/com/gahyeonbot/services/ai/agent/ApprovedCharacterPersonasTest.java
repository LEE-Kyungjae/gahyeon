package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.application.life.*;
import com.gahyeonbot.core.life.*;
import com.gahyeonbot.core.world.WorldId;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.ClassPathResource;
import java.time.Instant;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class ApprovedCharacterPersonasTest {
    @Test
    void configuredPersonasLoadWithIndependentMemoryAndSharedBehavior() throws Exception {
        var environment = new StandardEnvironment();
        for (var source : new YamlPropertySourceLoader().load("application", new ClassPathResource("application.yml"))) {
            environment.getPropertySources().addLast(source);
        }
        var properties = Binder.get(environment).bind("gahyeon.characters", CharacterCatalogProperties.class).get();
        var registry = new CharacterDefinitionRegistry(properties);
        assertThat(registry.all()).extracting(d -> d.id().value()).containsExactlyInAnyOrder(
                "gahyeon", "zeze", "rogue", "pirate", "fighter", "child", "hacker", "diana", "ururu", "stella-lily");
        // A costume must not create a second identity and a second memory namespace.
        assertThat(registry.all()).extracting(d -> d.id().value()).doesNotContain("fighter-unmasked");
        for (var definition : registry.all()) {
            var memories = mock(CharacterMemoryStore.class);
            String marker = "private-memory-for-" + definition.id().value();
            when(memories.recent(definition.id(), new WorldId("gahyeon-home"), "actor:42", 48))
                    .thenReturn(List.of(new CharacterMemory(0, definition.id(), new WorldId("gahyeon-home"),
                            "actor:42", CharacterMemoryKind.EPISODIC, marker, .7, .9, 0, null, Instant.EPOCH, Instant.EPOCH)));
            var provider = new AgentPromptProvider();
            provider.load();
            provider.configureCharacters(registry, memories);
            String prompt = provider.systemPrompt("unrelated-actor-history",
                    "character:" + definition.id().value() + ":gahyeon-home:actor:42|desktop:room", "오늘 무엇을 할까?");
            assertThat(prompt).contains(definition.displayName(), marker, "창작 설정", "실제 기억", "사용 가능한 도구를 사용한다",
                    "대기·처리 안내를 답변으로 생성하지 않는다").doesNotContain("unrelated-actor-history");
            verify(memories).recent(definition.id(), new WorldId("gahyeon-home"), "actor:42", 48);
            verifyNoMoreInteractions(memories);
            for (var other : registry.all()) {
                if (!other.id().equals(definition.id())) assertThat(prompt).doesNotContain("private-memory-for-" + other.id().value());
            }
        }
    }
}
