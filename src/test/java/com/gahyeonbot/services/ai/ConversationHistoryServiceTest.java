package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.ConversationHistory;
import com.gahyeonbot.repository.ConversationHistoryRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.data.domain.Pageable;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ConversationHistoryServiceTest {

    @Mock
    private ConversationHistoryRepository repository;

    @Mock
    private GlmService glmService;

    @Test
    void preservesUserAndAssistantRolesInChronologicalOrder() {
        ConversationHistory older = conversation(1L, "첫 질문", "첫 답");
        ConversationHistory newer = conversation(2L, "후속 질문", "후속 답");
        when(repository.findLatestSummary(eq(7L), any(Pageable.class))).thenReturn(List.of());
        when(repository.findRecentByUserId(eq(7L), any(Pageable.class)))
                .thenReturn(List.of(newer, older));

        var context = new ConversationHistoryService(repository, glmService).buildAgentContext(7L);

        assertThat(context.messages()).hasSize(4);
        assertThat(context.messages().get(0)).isInstanceOf(UserMessage.class);
        assertThat(context.messages().get(0).getText()).isEqualTo("첫 질문");
        assertThat(context.messages().get(1)).isInstanceOf(AssistantMessage.class);
        assertThat(context.messages().get(1).getText()).isEqualTo("첫 답");
        assertThat(context.messages().get(2).getText()).isEqualTo("후속 질문");
        assertThat(context.messages().get(3).getText()).isEqualTo("후속 답");
    }

    private ConversationHistory conversation(Long id, String user, String assistant) {
        return ConversationHistory.builder()
                .id(id)
                .userId(7L)
                .userMessage(user)
                .aiResponse(assistant)
                .createdAt(LocalDateTime.now())
                .build();
    }
}
