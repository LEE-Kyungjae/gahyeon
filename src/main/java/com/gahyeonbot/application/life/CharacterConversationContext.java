package com.gahyeonbot.application.life;

import com.gahyeonbot.core.life.CharacterId;
import com.gahyeonbot.core.session.ConversationSession;
import com.gahyeonbot.core.world.WorldId;
import java.util.Optional;

public record CharacterConversationContext(CharacterId characterId, WorldId worldId, String subjectId) {
    public static final String CHARACTER_KEY = "character.id";
    public static final String WORLD_KEY = "world.id";
    public static final String SUBJECT_ID_KEY = "memory.subject.id";
    public static final String SUBJECT_PERSISTENCE_KEY = "memory.subject.persistence";
    private static final String SESSION_PREFIX = "character:";

    public static Optional<CharacterConversationContext> from(ConversationSession session) {
        String character = session.clientContext().get(CHARACTER_KEY);
        if (character == null || character.isBlank()) return Optional.empty();
        String world = session.clientContext().getOrDefault(WORLD_KEY, "gahyeon-home");
        if ("ephemeral".equals(session.clientContext().get(SUBJECT_PERSISTENCE_KEY))) return Optional.empty();
        String subject = session.clientContext().getOrDefault(SUBJECT_ID_KEY,
                "principal:" + session.actorId().value());
        if (subject.isBlank()) return Optional.empty();
        return Optional.of(new CharacterConversationContext(
                new CharacterId(character), new WorldId(world), subject));
    }

    public String scopedSessionKey(String original) {
        return SESSION_PREFIX + characterId.value() + ":" + worldId.value() + ":" + subjectId + "|" + original;
    }

    public static Optional<CharacterConversationContext> fromScopedSessionKey(String sessionKey) {
        if (sessionKey == null || !sessionKey.startsWith(SESSION_PREFIX)) return Optional.empty();
        int separator = sessionKey.indexOf('|');
        if (separator < 0) return Optional.empty();
        String[] parts = sessionKey.substring(SESSION_PREFIX.length(), separator).split(":", 3);
        if (parts.length < 3 || parts[2].isBlank()) return Optional.empty();
        try {
            return Optional.of(new CharacterConversationContext(
                    new CharacterId(parts[0]), new WorldId(parts[1]), parts[2]));
        } catch (IllegalArgumentException ignored) {
            return Optional.empty();
        }
    }
}
