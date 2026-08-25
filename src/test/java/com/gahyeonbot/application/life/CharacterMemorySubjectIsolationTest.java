package com.gahyeonbot.application.life;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.life.CharacterId;
import com.gahyeonbot.core.life.CharacterMemory;
import com.gahyeonbot.core.life.CharacterMemoryKind;
import com.gahyeonbot.core.session.*;
import com.gahyeonbot.core.world.WorldId;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class CharacterMemorySubjectIsolationTest {
    @Test
    void recallNeverIncludesAnotherSubjectOrUnscopedMemory() {
        var store = new Store();
        store.append(memory("zezestudio:11111111-1111-1111-1111-111111111111", "A의 비밀"));
        store.append(memory("zezestudio:22222222-2222-2222-2222-222222222222", "B의 비밀"));
        store.append(memory(null, "공용처럼 보이는 이전 기억"));

        assertThat(store.recent(new CharacterId("gahyeon"), new WorldId("home"),
                "zezestudio:11111111-1111-1111-1111-111111111111", 10))
                .extracting(CharacterMemory::content)
                .containsExactly("A의 비밀");
    }

    @Test
    void uncertainSpeakerIsExcludedFromPersistentMemoryContext() {
        var session = new ConversationSession(new ConversationSessionId("voice:uncertain"), new ActorId(7),
                ClientSource.DISCORD, ConversationModality.VOICE,
                Map.of("character.id", "gahyeon", CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "ephemeral"));

        assertThat(CharacterConversationContext.from(session)).isEmpty();
    }

    @Test
    void scopedSessionKeyRoundTripsCanonicalSubjectWithoutLosingItsNamespace() {
        var session = new ConversationSession(new ConversationSessionId("discord:room"), new ActorId(7),
                ClientSource.DISCORD, ConversationModality.TEXT,
                Map.of("character.id", "gahyeon", "world.id", "home",
                        CharacterConversationContext.SUBJECT_ID_KEY,
                        "zezestudio:11111111-1111-1111-1111-111111111111"));
        var original = CharacterConversationContext.from(session).orElseThrow();

        assertThat(CharacterConversationContext.fromScopedSessionKey(original.scopedSessionKey("session")))
                .contains(original);
    }

    private static CharacterMemory memory(String subject, String content) {
        return new CharacterMemory(0, new CharacterId("gahyeon"), new WorldId("home"), subject,
                CharacterMemoryKind.SEMANTIC, content, 1, 1, 0, null, Instant.EPOCH, Instant.EPOCH);
    }

    private static final class Store implements CharacterMemoryStore {
        private final List<CharacterMemory> values = new ArrayList<>();
        public CharacterMemory append(CharacterMemory memory) { values.add(memory); return memory; }
        public List<CharacterMemory> recent(CharacterId characterId, WorldId worldId, int limit) {
            return values.stream().filter(value -> value.characterId().equals(characterId)
                    && value.worldId().equals(worldId)).limit(limit).toList();
        }
    }
}
