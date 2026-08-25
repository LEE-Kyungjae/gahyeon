package com.gahyeonbot.adapters.identity;

import com.gahyeonbot.application.life.CharacterConversationContext;
import com.gahyeonbot.application.life.MemorySubjectResolutionPort;
import com.gahyeonbot.core.identity.IdentityProvider;
import com.gahyeonbot.core.session.ConversationSession;
import com.gahyeonbot.repository.ExternalIdentityRepository;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Optional;
import java.util.UUID;

@Component
public final class JpaMemorySubjectResolutionAdapter implements MemorySubjectResolutionPort {
    private final ExternalIdentityRepository identities;

    public JpaMemorySubjectResolutionAdapter(ExternalIdentityRepository identities) {
        this.identities = identities;
    }

    @Override
    public ConversationSession resolve(ConversationSession session) {
        var context = new LinkedHashMap<>(session.clientContext());
        if ("ephemeral".equals(context.get(CharacterConversationContext.SUBJECT_PERSISTENCE_KEY))) {
            context.remove(CharacterConversationContext.SUBJECT_ID_KEY);
            return withContext(session, context);
        }
        identities.findByProviderAndPrincipal_Id(IdentityProvider.ZEZESTUDIO, session.actorId().value())
                .flatMap(identity -> canonicalUuid(identity.getExternalId()))
                .ifPresentOrElse(
                        uuid -> {
                            context.put(CharacterConversationContext.SUBJECT_ID_KEY, "zezestudio:" + uuid);
                            context.put(CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "durable");
                        },
                        () -> {
                            context.putIfAbsent(CharacterConversationContext.SUBJECT_ID_KEY,
                                    "principal:" + session.actorId().value());
                            context.putIfAbsent(CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "provisional");
                        });
        return withContext(session, context);
    }

    private static Optional<String> canonicalUuid(String value) {
        try {
            return Optional.of(UUID.fromString(value).toString());
        } catch (IllegalArgumentException invalid) {
            return Optional.empty();
        }
    }

    private static ConversationSession withContext(ConversationSession session, LinkedHashMap<String, String> context) {
        return new ConversationSession(session.id(), session.actorId(), session.source(), session.modality(), context);
    }
}
