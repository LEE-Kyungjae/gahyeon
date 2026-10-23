package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.memory.*;
import com.gahyeonbot.core.tool.ToolPolicy;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentRunRepository;
import com.gahyeonbot.services.ai.*;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.model.*;
import org.springframework.ai.chat.prompt.Prompt;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class AgentLookupRuntimeTest {
    private final ChatModel model = mock(ChatModel.class);
    private final NewsKnowledgeTools news = mock(NewsKnowledgeTools.class);
    private final AgentRunLedger ledger = mock(AgentRunLedger.class);
    private final MemoryUseCase memory = mock(MemoryUseCase.class);
    private DefaultAgentRuntime runtime() {
        var run = AgentRun.builder().id("lookup-test").actorId(42L)
                .status(AgentRunStatus.QUEUED).currentStep(0).maxSteps(8).build();
        when(ledger.create(any())).thenReturn(run);
        when(ledger.advanceStep(any(), any(), any())).thenReturn(run);
        when(memory.recall(any())).thenReturn(MemorySnapshot.EMPTY);
        var prompt = new AgentPromptProvider(); prompt.load();
        return new DefaultAgentRuntime(model, memory, ledger, mock(AgentRunRepository.class),
                mock(AgentApprovalService.class), new ToolPolicy(), prompt, new SimpleMeterRegistry(),
                mock(WeatherTools.class), mock(GitHubKnowledgeTools.class), mock(PaperKnowledgeTools.class),
                mock(KnowledgeFreshnessTools.class), news, new AgentRuntimeAvailability(5000, System::nanoTime));
    }
    private AgentRequest request(String text) {
        return new AgentRequest("lookup-test", "session", AgentModality.TEXT, null,
                new ActorId(42), "fixture", text, 8);
    }
    private ChatResponse answer(String text) {
        return new ChatResponse(List.of(new Generation(new AssistantMessage(text))));
    }
    private ChatResponse tool() {
        return new ChatResponse(List.of(new Generation(new AssistantMessage("", Map.of(),
                List.of(new AssistantMessage.ToolCall("c1", "function", "get_recent_personalized_news", "{}"))))));
    }
    @Test void correctsNewsOmissionOnceAndStreamsOnlyVerifiedFinalAnswer() {
        when(model.call(any(Prompt.class))).thenReturn(answer("조회 도구가 없어."), tool(), answer("오늘 기사: https://example.org/news"));
        when(news.getRecentPersonalizedNews()).thenReturn("source: internal verified personalized_news\nresult_count: 1\n  published_at: 2026-10-16T01:00:00+09:00\n  source: fixture | https://example.org/news");
        List<String> spoken = new ArrayList<>();
        var result = runtime().executeStreaming(request("오늘 읽으면 좋을 네이버기사있나?"), spoken::add);
        assertThat(spoken).containsExactly(result.content());
        verify(model, times(3)).call(any(Prompt.class));
        verify(news).getRecentPersonalizedNews();
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=news,outcome=EVIDENCE_AVAILABLE");
    }
    @Test void repeatedRefusalIsBoundedAndNeverRecordedAsFulfilled() {
        when(model.call(any(Prompt.class))).thenReturn(answer("조회하지 않았지만 최신 뉴스야."));
        var result = runtime().execute(request("오늘 뉴스 알려줘"));
        verify(model, times(2)).call(any(Prompt.class));
        assertThat(result.content()).contains("완료하지 못했어");
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=news,outcome=MISSING_TOOL_ATTEMPT");
    }
    @Test void emptyNewsIsNotMistakenForEvidence() {
        when(model.call(any(Prompt.class))).thenReturn(tool(), answer("기사가 있어."));
        when(news.getRecentPersonalizedNews()).thenReturn("knowledge_empty: 최근 24시간 동안 검증된 맞춤뉴스가 없어.");
        var result = runtime().execute(request("오늘 뉴스 알려줘"));
        assertThat(result.content()).contains("나오지 않았어");
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=news,outcome=NO_DATA");
    }
    @Test void failedTranslationCannotBecomeEvidence() {
        when(model.call(any(Prompt.class))).thenReturn(tool(), answer("확인했어."));
        when(news.getRecentPersonalizedNews()).thenReturn("knowledge_unavailable: 한국어 변환 실패");
        assertThat(runtime().execute(request("오늘 뉴스 알려줘")).content()).contains("완료하지 못했어");
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=news,outcome=TOOL_FAILED");
    }
    @Test void unavailableServerInspectionCannotClaimSuccess() {
        when(model.call(any(Prompt.class))).thenReturn(answer("서버를 점검했어. 정상이야."));
        assertThat(runtime().execute(request("지금 서버살펴봐")).content()).contains("확인하지 못했어");
        verify(model).call(any(Prompt.class));
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=server,outcome=BLOCKED_CAPABILITY");
    }
    @Test void cancellationDuringCorrectionPublishesNothing() {
        AtomicBoolean cancelled = new AtomicBoolean();
        when(model.call(any(Prompt.class))).thenReturn(answer("도구 없어."))
                .thenAnswer(inv -> {cancelled.set(true); return answer("잘못된 후속 답변");});
        List<String> spoken = new ArrayList<>();
        assertThatThrownBy(() -> runtime().executeStreaming(request("오늘 뉴스 알려줘"), spoken::add, cancelled::get))
                .isInstanceOf(AgentStreamCancelledException.class);
        assertThat(spoken).isEmpty();
        verify(ledger, never()).succeed(any(), any());
    }
    @Test void ordinaryChatDoesNotTriggerLookupCorrection() {
        when(model.call(any(Prompt.class))).thenReturn(answer("안녕!"));
        assertThat(runtime().execute(request("안녕")).content()).isEqualTo("안녕!");
        verify(model).call(any(Prompt.class));
        verify(ledger, never()).appendToolEvent(any(), eq(AgentEventType.TASK_EVIDENCE_ASSESSED), any(), any());
    }
    @Test void writingAndTranslationRequestsAreNotForcedIntoNewsLookup() {
        for (String text : List.of("오늘 뉴스라는 문장 번역해줘", "오늘 기사 작성해줘", "뉴스 조회하지 마", "뉴스 말고 농담해줘")) {
            assertThat(new AgentLookupEvidence(text).required()).as(text).isFalse();
        }
    }

    @Test void thrownToolFailureIsRecordedSeparatelyFromRunFailure() {
        when(model.call(any(Prompt.class))).thenReturn(tool());
        when(news.getRecentPersonalizedNews()).thenThrow(new IllegalStateException("fixture unavailable"));
        assertThatThrownBy(() -> runtime().execute(request("오늘 뉴스 알려줘")))
                .isInstanceOf(AgentExecutionException.class);
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=news,outcome=TOOL_FAILED");
        verify(ledger, never()).succeed(any(), any());
    }
    @Test void unavailableMarketQuoteCannotInventPrice() {
        when(model.call(any(Prompt.class))).thenReturn(answer("구리 시세는 999달러야."));
        assertThat(runtime().execute(request("LME 구리 시세 알려줘")).content()).doesNotContain("999");
        verify(ledger).appendToolEvent("lookup-test", AgentEventType.TASK_EVIDENCE_ASSESSED, null,
                "intent=market,outcome=BLOCKED_CAPABILITY");
    }
    @Test void insufficientStepBudgetNeverStartsCorrection() {
        when(model.call(any(Prompt.class))).thenReturn(answer("도구 없어."));
        var shortRequest = new AgentRequest("lookup-test", "session", AgentModality.TEXT, null,
                new ActorId(42), "fixture", "오늘 뉴스 알려줘", 1);
        runtime().execute(shortRequest);
        verify(model).call(any(Prompt.class));
    }

    @Test void configurationRollbackPreservesPreviousRuntimeBehavior() {
        when(model.call(any(Prompt.class))).thenReturn(answer("기존 응답"));
        var runtime = runtime();
        org.springframework.test.util.ReflectionTestUtils.setField(runtime, "lookupEvidenceEnabled", false);
        assertThat(runtime.execute(request("오늘 뉴스 알려줘")).content()).isEqualTo("기존 응답");
        verify(model).call(any(Prompt.class));
        verify(ledger, never()).appendToolEvent(any(), eq(AgentEventType.TASK_EVIDENCE_ASSESSED), any(), any());
    }

    private AgentRequest voiceRequest(String text) {
        return new AgentRequest("lookup-test", "session", AgentModality.VOICE, null,
                new ActorId(42), "fixture", text, 8);
    }
    @Test void regeneratesLengthLimitedVoiceReplyBeforeSpeaking() {
        var truncated = new ChatResponse(List.of(new Generation(new AssistantMessage("문장에서는 드릴게요로"),
                org.springframework.ai.chat.metadata.ChatGenerationMetadata.builder().finishReason("length").build())));
        when(model.call(any(Prompt.class))).thenReturn(truncated, answer("응, 문장이 끝나기 전에 잘린 문제야."));
        List<String> spoken = new ArrayList<>();
        var result = runtime().executeStreaming(voiceRequest("네 답변이 도중에 잘렸어"), spoken::add);
        assertThat(spoken).containsExactly(result.content());
        assertThat(result.content()).doesNotContain("드릴게요로");
        verify(model, times(2)).call(any(Prompt.class));
    }
    @Test void rejectsRepeatedCorruptLatinOutputAndVoiceDenial() {
        for (String bad : List.of("우리는 음성으로는 답변하지 않아요.",
                "MCP " + "tpfjdxeogkf tjfxim rimkrlska ".repeat(4))) {
            assertThat(VoiceReplyQuality.failure(bad, "stop")).isNotBlank();
        }
        assertThat(VoiceReplyQuality.failure("API와 OpenRouter 설정을 확인해야 해.", "stop")).isEmpty();
    }
    @Test void suppressesUnwantedSpokenPreambleWithoutRepeatingTheUserQuestion() {
        when(model.call(any(Prompt.class))).thenReturn(answer("음성으로 설명드릴게요.\n\n응, 임베드로 정정한 거 이해했어."));
        List<String> spoken = new ArrayList<>();
        var result = runtime().executeStreaming(voiceRequest("임베딩이 아니라 임베드다"), spoken::add);
        assertThat(result.content()).isEqualTo("응, 임베드로 정정한 거 이해했어.");
        assertThat(spoken).containsExactly(result.content());
        var captor = org.mockito.ArgumentCaptor.forClass(Prompt.class);
        verify(model).call(captor.capture());
        assertThat(captor.getValue().getInstructions().stream().map(m -> m.getText()).toList())
                .anyMatch(t -> t.contains("답변은 TTS로 재생된다") && t.contains("정정은 B로 이해"));
    }
    @Test void corruptedVoiceRepairIsBoundedAndDoesNotLeakDrafts() {
        when(model.call(any(Prompt.class))).thenReturn(answer("음성으로는 답변하지 않아요."));
        List<String> spoken = new ArrayList<>();
        var result = runtime().executeStreaming(voiceRequest("네 발음이 이상해"), spoken::add);
        verify(model, times(2)).call(any(Prompt.class));
        assertThat(spoken).containsExactly("응답을 완성하지 못했어.");
        assertThat(result.content()).isEqualTo(spoken.getFirst());
    }

    @Test void moderationClassifierIsNotSpokenAsAConversationReply() {
        when(model.call(any(Prompt.class))).thenReturn(answer("User Safety: safe\nResponse Safety: safe"), answer("응, 임베드로 정정한 거 이해했어."));
        List<String> spoken = new ArrayList<>();
        runtime().executeStreaming(voiceRequest("임베딩이 아니라 임베드다"), spoken::add);
        assertThat(spoken).containsExactly("응, 임베드로 정정한 거 이해했어.");
        verify(model, times(2)).call(any(Prompt.class));
    }
}
