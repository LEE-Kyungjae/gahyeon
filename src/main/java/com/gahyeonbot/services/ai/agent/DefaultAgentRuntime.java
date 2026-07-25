package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.services.ai.*;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.messages.*;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.DefaultToolCallingChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.ZonedDateTime;
import java.time.ZoneId;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class DefaultAgentRuntime implements AgentRuntime {
    private static final int REPEATED_TOOL_CALL_LIMIT = 3;
    private static final int MAX_EVENT_PAYLOAD = 4_000;

    private final ChatModel chatModel;
    private final ConversationHistoryService historyService;
    private final AgentRunLedger ledger;
    private final AgentToolPolicy toolPolicy;
    private final AgentPromptProvider promptProvider;
    private final MeterRegistry meterRegistry;
    private final WeatherTools weatherTools;
    private final GitHubKnowledgeTools gitHubKnowledgeTools;
    private final PaperKnowledgeTools paperKnowledgeTools;
    private final KnowledgeFreshnessTools knowledgeFreshnessTools;

    @Override
    public AgentResult execute(AgentRequest request) {
        long startedNanos = System.nanoTime();
        AgentRun run = ledger.create(request.toRunRequest());
        if (run.getStatus() == AgentRunStatus.SUCCEEDED) {
            return new AgentResult(run.getId(), run.getOutputText(), List.of(), Duration.ZERO);
        }
        if (run.getStatus() != AgentRunStatus.QUEUED) {
            throw new AgentExecutionException(
                    run.getId(), "RUN_NOT_ADMISSIBLE",
                    "이미 처리 중이거나 종료된 요청입니다: " + run.getStatus(), null);
        }

        List<String> usedTools = new ArrayList<>();
        try {
            ledger.transition(run.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
            ConversationHistoryService.AgentConversationContext memory = loadMemory(request.userId());
            List<Message> messages = initialMessages(request, memory);
            ToolCallback[] callbacks = MethodToolCallbackProvider.builder()
                    .toolObjects(weatherTools, gitHubKnowledgeTools, paperKnowledgeTools, knowledgeFreshnessTools)
                    .build()
                    .getToolCallbacks();
            Map<String, ToolCallback> callbackByName = new LinkedHashMap<>();
            for (ToolCallback callback : callbacks) {
                callbackByName.put(callback.getToolDefinition().name(), callback);
            }
            var options = DefaultToolCallingChatOptions.builder()
                    .toolCallbacks(callbacks)
                    .internalToolExecutionEnabled(false)
                    .build();
            Map<String, Integer> repeatedCalls = new HashMap<>();

            while (true) {
                AgentRun stepped = ledger.advanceStep(
                        run.getId(), AgentEventType.MODEL_CALL_STARTED, null);
                ChatResponse response = chatModel.call(new Prompt(messages, options));
                AssistantMessage assistant = response.getResult().getOutput();
                ledger.appendToolEvent(
                        run.getId(), AgentEventType.MODEL_CALL_COMPLETED, null,
                        "toolCalls=" + assistant.getToolCalls().size());
                messages.add(assistant);

                if (!assistant.hasToolCalls()) {
                    String content = assistant.getText() == null ? "" : assistant.getText().trim();
                    if (content.isBlank()) throw new IllegalStateException("모델의 최종 응답이 비어 있습니다.");
                    ledger.succeed(run.getId(), content);
                    historyService.saveConversation(request.userId(), request.message(), content);
                    Duration duration = Duration.ofNanos(System.nanoTime() - startedNanos);
                    recordMetrics(request.gateway(), "succeeded", duration);
                    return new AgentResult(run.getId(), content, usedTools, duration);
                }

                List<ToolResponseMessage.ToolResponse> toolResponses = new ArrayList<>();
                for (AssistantMessage.ToolCall toolCall : assistant.getToolCalls()) {
                    String signature = toolCall.name() + ":" + toolCall.arguments();
                    int repeats = repeatedCalls.merge(signature, 1, Integer::sum);
                    if (repeats >= REPEATED_TOOL_CALL_LIMIT) {
                        throw new IllegalStateException("동일한 도구 호출이 반복되었습니다: " + toolCall.name());
                    }
                    ToolCallback callback = callbackByName.get(toolCall.name());
                    if (callback == null) {
                        throw new IllegalStateException("등록되지 않은 도구입니다: " + toolCall.name());
                    }
                    AgentToolDecision decision = toolPolicy.decide(request.gateway(), toolCall.name());
                    ledger.appendToolEvent(run.getId(), AgentEventType.TOOL_CALL_REQUESTED,
                            toolCall.name(), limited(toolCall.arguments()));
                    if (decision == AgentToolDecision.DENY) {
                        throw new IllegalStateException("정책상 허용되지 않은 도구입니다: " + toolCall.name());
                    }
                    if (decision == AgentToolDecision.REQUIRE_APPROVAL) {
                        ledger.transition(run.getId(), AgentRunStatus.WAITING_APPROVAL,
                                AgentEventType.APPROVAL_REQUESTED, toolCall.name());
                        throw new AgentApprovalRequiredException(
                                run.getId(), toolCall.name(), toolCall.arguments());
                    }

                    ledger.appendToolEvent(
                            run.getId(), AgentEventType.TOOL_CALL_STARTED, toolCall.name(), null);
                    String toolResult;
                    try {
                        toolResult = callback.call(toolCall.arguments());
                    } catch (Exception toolFailure) {
                        ledger.appendToolEvent(run.getId(), AgentEventType.TOOL_CALL_FAILED,
                                toolCall.name(), limited(toolFailure.getMessage()));
                        throw toolFailure;
                    }
                    ledger.appendToolEvent(run.getId(), AgentEventType.TOOL_CALL_COMPLETED,
                            toolCall.name(), limited(toolResult));
                    usedTools.add(toolCall.name());
                    toolResponses.add(new ToolResponseMessage.ToolResponse(
                            toolCall.id(), toolCall.name(), toolResult));
                }
                messages.add(new ToolResponseMessage(toolResponses));

                if (stepped.getCurrentStep() >= request.maxSteps()) {
                    throw new AgentRunLedger.StepLimitExceededException(run.getId(), request.maxSteps());
                }
            }
        } catch (AgentApprovalRequiredException approval) {
            recordMetrics(request.gateway(), "waiting_approval",
                    Duration.ofNanos(System.nanoTime() - startedNanos));
            throw approval;
        } catch (Exception failure) {
            String errorCode = failure instanceof AgentRunLedger.StepLimitExceededException
                    ? "STEP_LIMIT_EXCEEDED"
                    : "AGENT_EXECUTION_FAILED";
            try {
                ledger.fail(run.getId(), errorCode, limited(failure.getMessage()));
            } catch (Exception ledgerFailure) {
                log.error("에이전트 실패 원장 기록 실패 run={}", run.getId(), ledgerFailure);
            }
            Duration duration = Duration.ofNanos(System.nanoTime() - startedNanos);
            recordMetrics(request.gateway(), "failed", duration);
            throw new AgentExecutionException(
                    run.getId(), errorCode, "에이전트 실행에 실패했습니다.", failure);
        }
    }

    private ConversationHistoryService.AgentConversationContext loadMemory(Long userId) {
        try {
            return historyService.buildAgentContext(userId);
        } catch (Exception e) {
            log.warn("에이전트 메모리 로드 실패 user={}", userId, e);
            return new ConversationHistoryService.AgentConversationContext("", List.of());
        }
    }

    private List<Message> initialMessages(
            AgentRequest request,
            ConversationHistoryService.AgentConversationContext memory) {
        List<Message> messages = new ArrayList<>();
        messages.add(new SystemMessage(promptProvider.systemPrompt(memory.summary())));
        messages.addAll(memory.messages());
        messages.add(new UserMessage("""
                [gateway]
                %s

                [현재 시각]
                %s

                [현재 질문]
                %s
                """.formatted(
                request.gateway(),
                ZonedDateTime.now(ZoneId.of("Asia/Seoul")),
                request.message())));
        return messages;
    }

    private void recordMetrics(AgentGateway gateway, String status, Duration duration) {
        meterRegistry.counter("gahyeonbot.agent.runs",
                "gateway", gateway.name().toLowerCase(Locale.ROOT),
                "status", status).increment();
        Timer.builder("gahyeonbot.agent.run.duration")
                .tag("gateway", gateway.name().toLowerCase(Locale.ROOT))
                .tag("status", status)
                .register(meterRegistry)
                .record(duration);
    }

    private static String limited(String value) {
        if (value == null) return null;
        return value.length() <= MAX_EVENT_PAYLOAD
                ? value
                : value.substring(0, MAX_EVENT_PAYLOAD) + "...[truncated]";
    }
}
