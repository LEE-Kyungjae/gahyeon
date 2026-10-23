package com.gahyeonbot.application.speech;

import com.gahyeonbot.application.conversation.GahyeonConversationService;
import com.gahyeonbot.core.conversation.*;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.session.*;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.env.MapPropertySource;
import java.util.Map;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class SttLearningWiringTest {
    @Test void springSelectsTheDecoratorAndHonorsGlobalDisable() {
        try (var context = new AnnotationConfigApplicationContext()) {
            var delegate = mock(GahyeonConversationService.class);
            var learning = mock(SttLearningService.class);
            context.getEnvironment().getPropertySources().addFirst(new MapPropertySource(
                    "test", Map.of("assistant.stt.learning-enabled", "false")));
            context.registerBean(GahyeonConversationService.class, () -> delegate);
            context.registerBean(SttLearningService.class, () -> learning);
            context.registerBean(AssistantProperties.class);
            context.register(SttLearningConversation.class);
            context.refresh();
            var selected = context.getBean(ConversationUseCase.class);
            assertThat(selected).isInstanceOf(SttLearningConversation.class);
            var request = new ConversationRequest("request", new ConversationSession(new ConversationSessionId("session"),
                    new ActorId(1), ClientSource.DISCORD, ConversationModality.VOICE,
                    Map.of("agent.toolScopeId", "42")), "user", "안녕");
            selected.converse(request);
            verify(delegate).converse(request);
            verifyNoInteractions(learning);
        }
    }
}
