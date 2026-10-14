package com.gahyeonbot.application.speech;

import com.gahyeonbot.application.conversation.GahyeonConversationService;
import com.gahyeonbot.core.conversation.*;
import com.gahyeonbot.core.session.ClientSource;
import com.gahyeonbot.core.session.ConversationModality;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Keeps transport, TTS, and the existing conversation runtime unchanged. */
@Service
@Primary
public class SttLearningConversation implements ConversationUseCase {
    private static final Logger log = LoggerFactory.getLogger(SttLearningConversation.class);
    private final GahyeonConversationService delegate;
    private final SttLearningService learning;
    private final AssistantProperties properties;
    private final boolean enabled;

    public SttLearningConversation(GahyeonConversationService delegate, SttLearningService learning,
            AssistantProperties properties, @Value("${assistant.stt.learning-enabled:true}") boolean enabled) {
        this.delegate = delegate;
        this.learning = learning;
        this.properties = properties;
        this.enabled = enabled;
    }

    @Override
    public ConversationResponse converse(ConversationRequest request) {
        var session = request.session();
        String guild = session.clientContext().get("agent.toolScopeId");
        if (enabled && session.source() == ClientSource.DISCORD && session.modality() == ConversationModality.VOICE
                && guild != null && guild.matches("[0-9]{1,20}")) {
            try {
                var stt = properties.getStt();
                // Fingerprint is the configured pipeline, not an assertion about which fallback answered.
                String pipeline = SttLearningService.hash("exact-v1", stt.getBaseUrl(), stt.getEndpoint(),
                        stt.getModel(), stt.getLanguage(), stt.getPrompt(), stt.getFallbackBaseUrl(),
                        stt.getFallbackEndpoint(), stt.getFallbackModel());
                var decision = learning.observe(session.actorId().value(), "discord:" + guild, pipeline,
                        request.requestId(), request.message());
                request = new ConversationRequest(request.requestId(), session, request.displayName(), decision.text());
                log.info("STT learning decision={} observation={}", decision.state(), decision.observationId());
            } catch (RuntimeException unavailable) {
                // A learning failure must not drop an otherwise usable voice question; never log its text.
                log.warn("STT learning bypass failureType={}", unavailable.getClass().getSimpleName());
            }
        }
        return delegate.converse(request);
    }
}
