package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.memory.MemorySnapshot;
import com.gahyeonbot.core.memory.MemoryUseCase;
import com.gahyeonbot.core.tool.ToolDecision;
import com.gahyeonbot.core.tool.ToolPolicy;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.entity.AgentSession;
import com.gahyeonbot.repository.AgentRunRepository;
import com.gahyeonbot.services.ai.*;
import com.gahyeonbot.services.ai.agent.skills.*;
import com.gahyeonbot.services.weather.WeatherService;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.model.*;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.ToolCallingChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.definition.ToolDefinition;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AgentSkillRuntimeIntegrationTest {
    @Test void realRuntimeSelectsSkillCallsNativeToolAndVerifiesBeforeSuccess() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), forecast(), answer("비가 와서 우산이 필요해요."));
        assertThat(f.runtime.execute(request()).content()).contains("우산");
        assertThat(f.journal.kinds()).containsExactly("selected", "attempt", "evidence", "verified");
        var prompts = org.mockito.ArgumentCaptor.forClass(Prompt.class);
        verify(f.model, times(3)).call(prompts.capture());
        var names = ((ToolCallingChatOptions) prompts.getAllValues().get(1).getOptions()).getToolCallbacks()
                .stream().map(tool -> tool.getToolDefinition().name()).toList();
        assertThat(names).contains("get_weather_forecast").doesNotContain("get_current_weather");
        verify(f.weather).buildForecastMessage(any(), any(), any());
        verify(f.ledger).succeed("run", "비가 와서 우산이 필요해요.");
    }

    @Test void prematureFinalAnswerIsBufferedAndCorrectedBeforeCommitting() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), answer("확인 완료"), forecast(), answer("확인한 예보입니다."));
        var observer = mock(AgentStreamObserver.class);
        assertThat(f.runtime.executeStreaming(request(), observer).content()).isEqualTo("확인한 예보입니다.");
        verify(observer, never()).onTextDelta(anyString());
        verify(f.model, never()).stream(any(Prompt.class));
        verify(f.ledger, never()).succeed("run", "확인 완료");
        verify(f.ledger).succeed("run", "확인한 예보입니다.");
    }

    @Test void cannotLoopForeverClaimingCompletionWithoutEvidence() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), answer("완료"));
        assertThatThrownBy(() -> f.runtime.execute(request())).isInstanceOf(AgentExecutionException.class);
        verify(f.model, times(8)).call(any(Prompt.class));
        verify(f.ledger, never()).succeed(anyString(), anyString());
        assertThat(f.journal.kinds()).doesNotContain("verified");
    }

    @Test void selectedSkillCannotExecuteUnlistedNativeTool() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), tool("get_current_weather", "{\"cityCode\":\"SEOUL\"}"));
        assertThatThrownBy(() -> f.runtime.execute(request())).isInstanceOf(AgentExecutionException.class);
        verify(f.weather, never()).buildCurrentWeatherMessage(any());
        verify(f.ledger, never()).succeed(anyString(), anyString());
    }

    @Test void selectionAndBusinessActionCannotBeBatchedToBypassNewScope() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(new ChatResponse(List.of(new Generation(
                new AssistantMessage("", Map.of(), List.of(
                        new AssistantMessage.ToolCall("1", "function", AgentSkillHarness.SELECT_TOOL,
                                "{\"id\":\"outing-weather\",\"version\":\"1.0.0\"}"),
                        new AssistantMessage.ToolCall("2", "function", "get_current_weather", "{\"cityCode\":\"SEOUL\"}")))))));
        assertThatThrownBy(() -> f.runtime.execute(request())).isInstanceOf(AgentExecutionException.class);
        assertThat(f.journal.entries).isEmpty();
        verifyNoInteractions(f.weather);
    }

    @Test void cancellationDuringToolCallCannotRecordEvidenceOrSuccess() {
        var f = new Fixture(true);
        var cancelled = new AtomicBoolean();
        when(f.model.call(any(Prompt.class))).thenReturn(select(), forecast());
        when(f.weather.buildForecastMessage(any(), any(), any())).thenAnswer(invocation -> {
            cancelled.set(true);
            return "result after cancellation";
        });
        assertThatThrownBy(() -> f.runtime.execute(request(), cancelled::get))
                .isInstanceOf(AgentStreamCancelledException.class);
        assertThat(f.journal.kinds()).containsExactly("selected", "attempt");
        verify(f.ledger, never()).succeed(anyString(), anyString());
    }

    @Test void disabledFactoryPreservesExistingNativeCallsWithoutSkillState() {
        var f = new Fixture(false);
        when(f.model.call(any(Prompt.class))).thenReturn(forecast(), answer("기존 답변"));
        assertThat(f.runtime.execute(request()).content()).isEqualTo("기존 답변");
        assertThat(f.journal.entries).isEmpty();
        var prompt = org.mockito.ArgumentCaptor.forClass(Prompt.class);
        verify(f.model, times(2)).call(prompt.capture());
        assertThat(((ToolCallingChatOptions) prompt.getAllValues().getFirst().getOptions()).getToolCallbacks())
                .extracting(c -> c.getToolDefinition().name()).doesNotContain(AgentSkillHarness.SELECT_TOOL);
    }

    @Test void failedNativeEvidenceCannotBecomeVerified() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), forecast());
        when(f.weather.buildForecastMessage(any(), any(), any())).thenReturn("서울 예보 데이터를 찾지 못했어.");
        assertThatThrownBy(() -> f.runtime.execute(request())).isInstanceOf(AgentExecutionException.class);
        assertThat(f.journal.kinds()).containsExactly("selected", "attempt");
        verify(f.ledger, never()).succeed(anyString(), anyString());
    }

    @Test void resumedApprovalRetainsSkillAndRequiresExactApprovalBeforeRemoteCall() {
        var f = new Fixture(true);
        var remote = mock(ToolCallback.class);
        when(remote.getToolDefinition()).thenReturn(ToolDefinition.builder().name("mcp_fixture_write")
                .description("reviewed").inputSchema("{\"type\":\"object\"}").build());
        when(remote.call("{}")).thenReturn("saved");
        var skill = new AgentSkill("fixture", "1.0.0", "problem", "when", Set.of("mcp_fixture_write"),
                Set.of("mcp_fixture_write"), 2, List.of("confirm saved"), "procedure", AgentSkill.sha256("fixture"));
        ApprovedMcpTools provider = () -> List.of(new AgentToolRegistry.Binding(
                "mcp:fixture", remote, ToolDecision.REQUIRE_APPROVAL, Set.of(42L), 7L));
        ReflectionTestUtils.setField(f.runtime, "skillHarnessFactory", new AgentSkillHarnessFactory(
                new AgentSkillCatalog(List.of(skill)), f.journal, List.of(provider), true));
        when(f.model.call(any(Prompt.class))).thenReturn(
                tool(AgentSkillHarness.SELECT_TOOL, "{\"id\":\"fixture\",\"version\":\"1.0.0\"}"),
                tool("mcp_fixture_write", "{}"), tool("mcp_fixture_write", "{}"), answer("saved"));
        when(f.approvals.request("run", "mcp_fixture_write", "{}"))
                .thenReturn(com.gahyeonbot.entity.AgentApproval.builder().id("approval").build());
        assertThatThrownBy(() -> f.runtime.execute(request())).isInstanceOf(AgentApprovalRequiredException.class);
        verify(remote, never()).call(anyString());
        assertThat(f.journal.kinds()).containsExactly("selected");
        f.run.setStatus(AgentRunStatus.WAITING_APPROVAL);
        when(f.runs.findByIdWithSession("run")).thenReturn(Optional.of(f.run));
        when(f.approvals.hasApproved("run")).thenReturn(true);
        when(f.approvals.consumeIfApproved("run", "mcp_fixture_write", "{}")).thenReturn(true);
        assertThat(f.runtime.resume("run", new ActorId(42)).content()).isEqualTo("saved");
        verify(remote, times(1)).call("{}");
        assertThat(f.journal.kinds()).containsExactly("selected", "attempt", "evidence", "verified");
    }

    @Test void backgroundResumeUsesPersistedEvidenceAndProcedure() {
        var f = new Fixture(true);
        var skill = new AgentSkillCatalog().require("outing-weather", "1.0.0");
        f.journal.entries.add(new AgentSkillJournal.Entry("selected", skill.id(), skill.version(), skill.digest(), null, null));
        f.journal.entries.add(new AgentSkillJournal.Entry("attempt", skill.id(), skill.version(), skill.digest(), "get_weather_forecast", null));
        f.journal.entries.add(new AgentSkillJournal.Entry("evidence", skill.id(), skill.version(), skill.digest(), "get_weather_forecast", AgentSkill.sha256("result")));
        f.run.setStatus(AgentRunStatus.WAITING_BACKGROUND);
        when(f.runs.findByIdWithSession("run")).thenReturn(Optional.of(f.run));
        when(f.model.call(any(Prompt.class))).thenReturn(answer("추가 확인 결과입니다."));
        assertThat(f.runtime.resumeBackground("run", "background result").content()).contains("추가");
        var prompt = org.mockito.ArgumentCaptor.forClass(Prompt.class);
        verify(f.model).call(prompt.capture());
        assertThat(prompt.getValue().getInstructions().toString()).contains("outing-weather@1.0.0");
        verifyNoInteractions(f.weather);
        assertThat(f.journal.kinds()).endsWith("verified");
    }

    @Test void disablingFeatureCannotResumeSkilledRunWithoutItsRestrictions() {
        var f = new Fixture(false);
        var skill = new AgentSkillCatalog().require("outing-weather", "1.0.0");
        f.journal.entries.add(new AgentSkillJournal.Entry("selected", skill.id(), skill.version(), skill.digest(), null, null));
        f.run.setCurrentStep(2);
        f.run.setStatus(AgentRunStatus.WAITING_BACKGROUND);
        when(f.runs.findByIdWithSession("run")).thenReturn(Optional.of(f.run));
        assertThatThrownBy(() -> f.runtime.resumeBackground("run", "background result"))
                .isInstanceOf(AgentExecutionException.class).hasRootCauseMessage(
                        "Skill execution disabled; restart the paused request explicitly");
        verifyNoInteractions(f.model, f.weather);
        verify(f.ledger, never()).succeed(anyString(), anyString());
    }

    @Test void cancellationBeforeFinalCommitDoesNotVerifyOrRememberCompletion() {
        var f = new Fixture(true);
        when(f.model.call(any(Prompt.class))).thenReturn(select(), forecast(), answer("완료"));
        AgentExecutionControl control = new AgentExecutionControl() {
            public boolean isCancelled() { return false; }
            public boolean commitIfActive(Runnable commit) { return false; }
        };
        assertThatThrownBy(() -> f.runtime.execute(request(), control)).isInstanceOf(AgentExecutionException.class);
        assertThat(f.journal.kinds()).containsExactly("selected", "attempt", "evidence");
        verify(f.ledger, never()).succeed(anyString(), anyString());
    }

    private static AgentRequest request() {
        return new AgentRequest("request", "session", AgentModality.TEXT, 7L, new ActorId(42), "fixture", "서울 외출 준비", 8);
    }
    private static ChatResponse select() {
        return tool(AgentSkillHarness.SELECT_TOOL, "{\"id\":\"outing-weather\",\"version\":\"1.0.0\"}");
    }
    private static ChatResponse forecast() {
        String day = LocalDate.now(ZoneId.of("Asia/Seoul")).toString();
        return tool("get_weather_forecast", "{\"cityCode\":\"SEOUL\",\"startDate\":\"" + day + "\",\"endDate\":\"" + day + "\"}");
    }
    private static ChatResponse tool(String name, String args) {
        return new ChatResponse(List.of(new Generation(new AssistantMessage("", Map.of(),
                List.of(new AssistantMessage.ToolCall("call", "function", name, args))))));
    }
    private static ChatResponse answer(String text) {
        return new ChatResponse(List.of(new Generation(new AssistantMessage(text))));
    }
    private static class Journal implements AgentSkillJournal {
        final List<Entry> entries = new ArrayList<>();
        public List<Entry> read(String runId) { return List.copyOf(entries); }
        public void append(String runId, Entry entry) { entries.add(entry); }
        List<String> kinds() { return entries.stream().map(Entry::kind).toList(); }
    }
    private static class Fixture {
        final ChatModel model = mock(ChatModel.class);
        final AgentRunLedger ledger = mock(AgentRunLedger.class);
        final AgentRunRepository runs = mock(AgentRunRepository.class);
        final AgentApprovalService approvals = mock(AgentApprovalService.class);
        final WeatherService weather = mock(WeatherService.class);
        final Journal journal = new Journal();
        final AgentRun run = AgentRun.builder().id("run").requestId("request").actorId(42L)
                .session(AgentSession.builder().sessionKey("session").build()).modality(AgentModality.TEXT)
                .toolScopeId(7L).actorDisplayName("fixture").inputText("서울 외출 준비")
                .status(AgentRunStatus.QUEUED).currentStep(0).maxSteps(8).build();
        final DefaultAgentRuntime runtime;
        Fixture(boolean enabled) {
            var memory = mock(MemoryUseCase.class);
            when(memory.recall(any())).thenReturn(MemorySnapshot.EMPTY);
            when(weather.buildForecastMessage(any(), any(), any())).thenReturn("서울 예보: 비, 18~22°C");
            when(ledger.create(any())).thenReturn(run);
            when(ledger.advanceStep(anyString(), any(), any())).thenAnswer(invocation -> {
                if (run.getCurrentStep() >= run.getMaxSteps()) throw new AgentRunLedger.StepLimitExceededException("run", 8);
                run.setCurrentStep(run.getCurrentStep() + 1);
                return run;
            });
            var prompt = new AgentPromptProvider();
            prompt.load();
            runtime = new DefaultAgentRuntime(model, memory, ledger, runs, approvals, new ToolPolicy(), prompt,
                    new SimpleMeterRegistry(), new WeatherTools(weather), mock(GitHubKnowledgeTools.class),
                    mock(PaperKnowledgeTools.class), mock(KnowledgeFreshnessTools.class), mock(NewsKnowledgeTools.class),
                    new AgentRuntimeAvailability(5000, System::nanoTime));
            ReflectionTestUtils.setField(runtime, "skillHarnessFactory", new AgentSkillHarnessFactory(
                    new AgentSkillCatalog(), journal, List.of(), enabled));
        }
    }
}
