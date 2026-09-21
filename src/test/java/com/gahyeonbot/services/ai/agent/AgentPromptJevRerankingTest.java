package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.application.life.*;
import com.gahyeonbot.core.life.*;
import com.gahyeonbot.core.world.WorldId;
import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

class AgentPromptJevRerankingTest {
    @Test void filtersScopeAndExpiryBeforeRerankingAndLimitsFinalContext() {
        CharacterId character = new CharacterId("gahyeon");
        WorldId world = new WorldId("gahyeon-home");
        var all = new ArrayList<CharacterMemory>();
        for (int i = 0; i < 30; i++) all.add(new CharacterMemory(i, character, world, "actor:42",
                CharacterMemoryKind.SEMANTIC, "memory-" + i, 1 - i * .01, 1, 0, null, Instant.now(), Instant.now()));
        all.add(new CharacterMemory(50, character, world, "actor:77", CharacterMemoryKind.SEMANTIC,
                "other-user", 1, 1, 0, null, Instant.now(), Instant.now()));
        all.add(new CharacterMemory(51, character, world, "actor:42", CharacterMemoryKind.SEMANTIC,
                "expired", 1, 1, 0, Instant.EPOCH, Instant.EPOCH, Instant.EPOCH));
        var provider = new AgentPromptProvider();
        provider.load();
        provider.configureCharacters(new CharacterDefinitionRegistry(CharacterCatalogProperties.standard()), new CharacterMemoryStore() {
            public CharacterMemory append(CharacterMemory value) { return value; }
            public List<CharacterMemory> recent(CharacterId id, WorldId worldId, int limit) { return all; }
        });
        provider.configureMemoryReranker((query, candidates) -> {
            assertThat(query).isEqualTo("current question");
            assertThat(candidates).hasSize(24).allMatch(value -> "actor:42".equals(value.subjectId()) && !value.expiredAt(Instant.now()));
            var reversed = new ArrayList<>(candidates);
            Collections.reverse(reversed);
            return reversed;
        });
        String prompt = provider.systemPrompt(null, "character:gahyeon:gahyeon-home:actor:42|desktop:room", "current question");
        assertThat(prompt).contains("memory-23", "memory-8").doesNotContain("memory-0\n", "other-user", "expired");
        assertThat(prompt.split("- \\[semantic\\]", -1)).hasSize(17);
    }
}
