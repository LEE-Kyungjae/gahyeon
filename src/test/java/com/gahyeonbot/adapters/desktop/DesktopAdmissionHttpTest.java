package com.gahyeonbot.adapters.desktop;

import com.gahyeonbot.application.conversation.ConversationStreamingUseCase;
import com.gahyeonbot.application.identity.IdentityResolutionUseCase;
import com.gahyeonbot.core.conversation.ConversationRejectedException;
import com.gahyeonbot.core.identity.ActorId;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Exercises actual MVC exception resolution, not direct controller invocation. */
class DesktopAdmissionHttpTest {
    @Test void unsafeInputReturnsTyped422WithoutLeakingExceptionDetails() throws Exception {
        assertRejection(ConversationRejectedException.Reason.UNSAFE_INPUT, 422);
    }

    @Test void rateLimitReturnsTyped429AndFinishesGeneration() throws Exception {
        assertRejection(ConversationRejectedException.Reason.RATE_LIMITED, 429);
    }

    private void assertRejection(ConversationRejectedException.Reason reason, int expectedStatus) throws Exception {
        var conversation = mock(ConversationStreamingUseCase.class);
        var identities = mock(IdentityResolutionUseCase.class);
        var streams = mock(DesktopEventStreamService.class);
        when(identities.resolveExternal(any(), any(), any(), isNull())).thenReturn(new ActorId(42));
        when(streams.beginConversation("qa-session")).thenReturn("qa-generation");
        when(conversation.converseStreaming(any(), any())).thenThrow(new ConversationRejectedException(
                reason, "private input must never be serialized", new IllegalStateException("private cause")));
        var controller = new DesktopConversationController(conversation, identities, streams,
                mock(DesktopSessionOwnership.class), mock(DesktopCredentialAuthorization.class));
        var mvc = MockMvcBuilders.standaloneSetup(controller).build();
        try {
            mvc.perform(post("/gahyeon/desktop/conversations/qa-session/messages")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                            {"installationId":"qa-install","displayName":"tester","message":"fixture"}
                            """))
                    .andExpect(status().is(expectedStatus))
                    .andExpect(jsonPath("code").value(reason.name()))
                    .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("private"))));
        } finally {
            verify(streams).finishConversation("qa-session", "qa-generation");
        }
    }
}
