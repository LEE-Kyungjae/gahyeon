package com.gahyeonbot.application.life;

import com.gahyeonbot.core.session.ConversationSession;

/** Resolves the stable, authorization-scoped owner of conversational memory. */
public interface MemorySubjectResolutionPort {
    ConversationSession resolve(ConversationSession session);

    static MemorySubjectResolutionPort passthrough() {
        return session -> session;
    }
}
