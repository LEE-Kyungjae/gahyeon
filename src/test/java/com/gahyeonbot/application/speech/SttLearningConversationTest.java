package com.gahyeonbot.application.speech;

import com.gahyeonbot.application.conversation.GahyeonConversationService;
import com.gahyeonbot.core.conversation.*;
import com.gahyeonbot.core.session.*;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.util.Map;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class SttLearningConversationTest {
    @Test void forwardsCorrectedVoiceOnlyAndKeepsActorAndRequestIdentity() {
        var delegate = mock(GahyeonConversationService.class);
        var learning = mock(SttLearningService.class);
        when(learning.observe(eq(7L), eq("discord:42"), anyString(), eq("req"), eq("원문")))
                .thenReturn(new SttLearningService.Decision("observation", "정정문", "APPLIED"));
        var wrapper = new SttLearningConversation(delegate, learning, new AssistantProperties(), true);
        var voice = request(ConversationModality.VOICE);
        wrapper.converse(voice);
        var captured = ArgumentCaptor.forClass(ConversationRequest.class);
        verify(delegate).converse(captured.capture());
        assertThat(captured.getValue().message()).isEqualTo("정정문");
        assertThat(captured.getValue().session()).isSameAs(voice.session());
        assertThat(captured.getValue().requestId()).isEqualTo("req");
    }

    @Test void bypassesTextAndDisabledModeAndDatabaseFailuresWithoutDroppingQuestion() {
        var delegate = mock(GahyeonConversationService.class);
        var learning = mock(SttLearningService.class);
        var wrapper = new SttLearningConversation(delegate, learning, new AssistantProperties(), true);
        var text = request(ConversationModality.TEXT);
        wrapper.converse(text);
        verifyNoInteractions(learning);
        verify(delegate).converse(text);
        var voice = request(ConversationModality.VOICE);
        new SttLearningConversation(delegate, learning, new AssistantProperties(), false).converse(voice);
        verifyNoInteractions(learning);
        when(learning.observe(anyLong(), anyString(), anyString(), anyString(), anyString()))
                .thenThrow(new IllegalStateException("database unavailable"));
        wrapper.converse(voice);
        verify(delegate, times(2)).converse(voice);
    }

    private ConversationRequest request(ConversationModality modality) {
        return new ConversationRequest("req", new ConversationSession(new ConversationSessionId("voice:42"),
                new ActorId(7), ClientSource.DISCORD, modality, Map.of("agent.toolScopeId", "42")), "name", "원문");
    }
}
