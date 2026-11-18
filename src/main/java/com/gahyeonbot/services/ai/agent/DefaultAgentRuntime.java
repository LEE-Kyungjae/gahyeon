package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.memory.MemorySnapshot;
import com.gahyeonbot.core.memory.MemoryUseCase;
import com.gahyeonbot.core.tool.ToolPolicy;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentRunRepository;
import com.gahyeonbot.services.ai.*;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.messages.*;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.DefaultToolCallingChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

import static com.gahyeonbot.services.ai.agent.AgentCancellation.cancelled;
import static com.gahyeonbot.services.ai.agent.AgentCancellation.ensureNotCancelled;
import static com.gahyeonbot.services.ai.agent.AgentEventPayloads.limited;

@Service
@ConditionalOnProperty(name = "spring.ai.model.chat", havingValue = "openai")
@RequiredArgsConstructor
@Slf4j
public class DefaultAgentRuntime implements AgentRuntime {
    private static final int REPEATED_TOOL_CALL_LIMIT = 3;
    private static final int EMPTY_FINAL_RESPONSE_RETRY_LIMIT = 1;
    private static final String EMPTY_FINAL_RESPONSE_FALLBACK =
            "답변을 정리하는 중 문제가 생겼어요. 같은 질문을 한 번만 다시 말해 주세요.";

    private final ChatModel chatModel;
    private final MemoryUseCase memoryUseCase;
    private final AgentRunLedger ledger;
    private final AgentRunRepository runRepository;
    private final AgentApprovalService approvalService;
    private final ToolPolicy toolPolicy;
    private final AgentPromptProvider promptProvider;
    private final MeterRegistry meterRegistry;
    private final WeatherTools weatherTools;
    private final GitHubKnowledgeTools gitHubKnowledgeTools;
    private final PaperKnowledgeTools paperKnowledgeTools;
    private final KnowledgeFreshnessTools knowledgeFreshnessTools;
    private final AgentRuntimeAvailability availability;

    @Value("${gahyeon.agent.streaming.tool-text-exclusive-enabled:false}")
    private boolean toolTextExclusiveStreamingEnabled;
    @Value("${spring.ai.openai.base-url:}")
    private String configuredBaseUrl;
    @Value("${spring.ai.openai.chat.options.model:}")
    private String configuredModel;
    @Value("${gahyeon.agent.streaming.verified-base-url:}")
    private String verifiedStreamingBaseUrl;
    @Value("${gahyeon.agent.streaming.verified-model:}")
    private String verifiedStreamingModel;
    private final AtomicBoolean streamingContractHealthy = new AtomicBoolean(true);

    @Override
    public boolean isReady() {
        return availability.isReady();
    }

    @Override
    public AgentResult execute(AgentRequest request) {
        return execute(request, null, AgentExecutionControl.NONE);
    }

    @Override
    public AgentResult execute(AgentRequest request, AgentExecutionControl control) {
        return execute(request, null, Objects.requireNonNull(control, "execution control"));
    }

    @Override
    public AgentResult executeStreaming(AgentRequest request, AgentStreamObserver observer) {
        return execute(
                request,
                Objects.requireNonNull(observer, "stream observer"),
                AgentExecutionControl.NONE);
    }

    @Override
    public AgentResult executeStreaming(
            AgentRequest request,
            AgentStreamObserver observer,
            AgentExecutionControl control) {
        AgentStreamObserver delegate = Objects.requireNonNull(observer, "stream observer");
        AgentExecutionControl executionControl = Objects.requireNonNull(control, "execution control");
        AgentStreamObserver guarded = new AgentStreamObserver() {
            @Override
            public void onTextDelta(String delta) {
                if (isCancelled()) throw new AgentStreamCancelledException();
                delegate.onTextDelta(delta);
            }

            @Override
            public boolean isCancelled() {
                return executionControl.isCancelled() || delegate.isCancelled();
            }
        };
        return execute(
                request,
                guarded,
                executionControl);
    }

    private AgentResult execute(
            AgentRequest request,
            AgentStreamObserver observer,
            AgentExecutionControl control) {
        long startedNanos = System.nanoTime();
        ensureNotCancelled(observer, control);
        AgentRun run = ledger.create(request.toRunRequest());
        if (run.getStatus() == AgentRunStatus.SUCCEEDED) {
            ensureNotCancelled(observer, control);
            return new AgentResult(run.getId(), run.getOutputText(), List.of(), Duration.ZERO);
        }
        if (run.getStatus() != AgentRunStatus.QUEUED) {
            throw new AgentExecutionException(
                    run.getId(), "RUN_NOT_ADMISSIBLE",
                    "이미 처리 중이거나 종료된 요청입니다: " + run.getStatus(), null);
        }

        ledger.startInteractiveRun(
                run.getId(), request.actorId(), "client_generation_changed");
        control.onRunStarted(
                run.getId(),
                () -> cancelRun(run.getId(), request.actorId(), "client_generation_changed"));
        ensureNotCancelled(observer, control);
        return runLoop(request, run, startedNanos, null, observer, control);
    }

    @Override
    public AgentResult resume(String runId, ActorId actorId) {
        AgentRun run = runRepository.findByIdWithSession(runId)
                .orElseThrow(() -> new IllegalArgumentException("실행을 찾을 수 없습니다: " + runId));
        if (run.getActorId() != actorId.value()) {
            throw new SecurityException("이 실행을 재개할 권한이 없습니다.");
        }
        if (run.getStatus() != AgentRunStatus.WAITING_APPROVAL) {
            throw new IllegalStateException("승인 대기 실행만 재개할 수 있습니다: " + run.getStatus());
        }
        if (!approvalService.hasApproved(runId)) {
            throw new IllegalStateException("승인된 도구 호출이 없습니다.");
        }
        AgentRequest request = new AgentRequest(
                run.getRequestId(),
                run.getSession().getSessionKey(),
                run.getModality(),
                run.getToolScopeId(),
                new ActorId(run.getActorId()),
                run.getActorDisplayName(),
                run.getInputText(),
                run.getMaxSteps());
        ledger.claimResume(
                runId,
                AgentRunStatus.WAITING_APPROVAL,
                AgentEventType.RUN_RESUMED,
                "approval");
        return runLoop(
                request, run, System.nanoTime(), null, null, AgentExecutionControl.NONE);
    }

    @Override
    public AgentResult resumeBackground(String runId, String backgroundResult) {
        AgentRun run = runRepository.findByIdWithSession(runId)
                .orElseThrow(() -> new IllegalArgumentException("실행을 찾을 수 없습니다: " + runId));
        if (run.getStatus() != AgentRunStatus.WAITING_BACKGROUND) {
            throw new IllegalStateException("백그라운드 대기 실행만 재개할 수 있습니다: " + run.getStatus());
        }
        AgentRequest request = new AgentRequest(
                run.getRequestId(),
                run.getSession().getSessionKey(),
                run.getModality(),
                run.getToolScopeId(),
                new ActorId(run.getActorId()),
                run.getActorDisplayName(),
                run.getInputText(),
                run.getMaxSteps());
        ledger.claimResume(
                runId,
                AgentRunStatus.WAITING_BACKGROUND,
                AgentEventType.BACKGROUND_RESULT_RECEIVED,
                limited(backgroundResult));
        return runLoop(
                request, run, System.nanoTime(), backgroundResult, null,
                AgentExecutionControl.NONE);
    }

    private AgentResult runLoop(
            AgentRequest request,
            AgentRun run,
            long startedNanos,
            String backgroundResult,
            AgentStreamObserver streamObserver,
            AgentExecutionControl control) {
        List<String> usedTools = new ArrayList<>();
        AgentRunMetrics metrics = new AgentRunMetrics(meterRegistry);
        try {
            MemorySnapshot memory = loadMemory(request.actorId());
            List<Message> messages = new AgentConversationPrompt(promptProvider)
                    .initialMessages(request, memory, backgroundResult);
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
            AgentToolCallExecutor toolCallExecutor = new AgentToolCallExecutor(
                    ledger, toolPolicy, approvalService, callbackByName,
                    new AgentLoopGuard(REPEATED_TOOL_CALL_LIMIT));
            int emptyFinalResponseRetries = 0;

            while (true) {
                ensureNotCancelled(streamObserver, control);
                AgentRun stepped = ledger.advanceStep(
                        run.getId(), AgentEventType.MODEL_CALL_STARTED, null);
                if (!availability.tryAcquireProviderCall()) {
                    meterRegistry.counter("gahyeonbot.agent.provider.circuit.rejections").increment();
                    throw new AgentProviderUnavailableException();
                }
                ChatResponse response;
                try {
                    response = new ToolSafeChatStreamer(
                            chatModel,
                            StreamingModelVerification.allows(
                                    toolTextExclusiveStreamingEnabled,
                                    configuredBaseUrl,
                                    configuredModel,
                                    verifiedStreamingBaseUrl,
                                    verifiedStreamingModel)
                                    && streamingContractHealthy.get())
                            .call(new Prompt(messages, options), streamObserver);
                } catch (ToolStreamingContractViolationException violation) {
                    availability.recordProviderSuccess();
                    streamingContractHealthy.set(false);
                    meterRegistry.counter("gahyeonbot.agent.streaming.contract.violations").increment();
                    log.error("모델 streaming tool/text 배타 계약 위반; 이후 요청은 동기 fallback 사용", violation);
                    throw violation;
                } catch (ModelProviderException providerFailure) {
                    if (cancelled(streamObserver, control)) {
                        availability.recordProviderSuccess();
                        throw new AgentStreamCancelledException(providerFailure);
                    }
                    availability.recordProviderFailure();
                    meterRegistry.counter("gahyeonbot.agent.provider.failures").increment();
                    throw providerFailure;
                } catch (AgentStreamCancelledException
                         | AgentStreamObserverDeliveryException nonProviderFailure) {
                    availability.recordProviderSuccess();
                    throw nonProviderFailure;
                }
                availability.recordProviderSuccess();
                ensureNotCancelled(streamObserver, control);
                AssistantMessage assistant = response.getResult().getOutput();
                ledger.appendToolEvent(
                        run.getId(), AgentEventType.MODEL_CALL_COMPLETED, null,
                        "toolCalls=" + assistant.getToolCalls().size());
                messages.add(assistant);

                if (!assistant.hasToolCalls()) {
                    String content = sanitizeFinalResponse(assistant.getText());
                    if (content.isBlank()
                            && emptyFinalResponseRetries < EMPTY_FINAL_RESPONSE_RETRY_LIMIT
                            && stepped.getCurrentStep() < request.maxSteps()) {
                        emptyFinalResponseRetries++;
                        meterRegistry.counter("gahyeonbot.agent.empty_final_response.retries").increment();
                        log.warn("빈 최종 응답 교정 재시도 run={} retry={}",
                                run.getId(), emptyFinalResponseRetries);
                        messages.add(new UserMessage("""
                                [출력 교정]
                                내부 추론이나 태그를 출력하지 말고, 사용자의 질문에 대한 최종 답변만 한국어로 작성해.
                                """));
                        continue;
                    }
                    if (content.isBlank()) {
                        meterRegistry.counter("gahyeonbot.agent.empty_final_response.fallbacks").increment();
                        log.error("빈 최종 응답 교정 실패; 안전 응답 사용 run={}", run.getId());
                        content = EMPTY_FINAL_RESPONSE_FALLBACK;
                    }
                    String finalContent = content;
                    boolean committed = control.commitIfActive(() -> {
                        ensureNotCancelled(streamObserver, control);
                        ledger.succeed(run.getId(), finalContent);
                        if (usesSharedActorMemory(request.sessionKey())) {
                            memoryUseCase.remember(request.actorId(), request.message(), finalContent);
                        }
                    });
                    if (!committed) throw new AgentStreamCancelledException();
                    Duration duration = Duration.ofNanos(System.nanoTime() - startedNanos);
                    metrics.record(request.modality(), "succeeded", duration);
                    return new AgentResult(run.getId(), finalContent, usedTools, duration);
                }

                List<ToolResponseMessage.ToolResponse> toolResponses = toolCallExecutor.executeAll(
                        run.getId(), assistant.getToolCalls(), streamObserver, control, usedTools);
                messages.add(new ToolResponseMessage(toolResponses));

                if (stepped.getCurrentStep() >= request.maxSteps()) {
                    throw new AgentRunLedger.StepLimitExceededException(run.getId(), request.maxSteps());
                }
            }
        } catch (AgentApprovalRequiredException approval) {
            if (cancelled(streamObserver, control)) {
                cancelRun(run.getId(), request.actorId(), "client_generation_changed");
                metrics.record(request.modality(), "cancelled",
                        Duration.ofNanos(System.nanoTime() - startedNanos));
                throw new AgentStreamCancelledException(approval);
            }
            metrics.record(request.modality(), "waiting_approval",
                    Duration.ofNanos(System.nanoTime() - startedNanos));
            throw approval;
        } catch (Exception failure) {
            if (cancelled(streamObserver, control)) {
                cancelRun(run.getId(), request.actorId(), "client_generation_changed");
                Duration duration = Duration.ofNanos(System.nanoTime() - startedNanos);
                metrics.record(request.modality(), "cancelled", duration);
                if (failure instanceof AgentStreamCancelledException cancelled) throw cancelled;
                throw new AgentStreamCancelledException(failure);
            }
            String errorCode = failure instanceof AgentRunLedger.StepLimitExceededException
                    ? "STEP_LIMIT_EXCEEDED"
                    : "AGENT_EXECUTION_FAILED";
            try {
                ledger.fail(run.getId(), errorCode, limited(failure.getMessage()));
            } catch (Exception ledgerFailure) {
                log.error("에이전트 실패 원장 기록 실패 run={}", run.getId(), ledgerFailure);
            }
            Duration duration = Duration.ofNanos(System.nanoTime() - startedNanos);
            metrics.record(request.modality(), "failed", duration);
            throw new AgentExecutionException(
                    run.getId(), errorCode, "에이전트 실행에 실패했습니다.", failure);
        }
    }

    private void cancelRun(String runId, ActorId actorId, String reason) {
        try {
            ledger.cancel(runId, actorId, reason);
        } catch (Exception ledgerFailure) {
            log.error("에이전트 취소 원장 기록 실패 run={}", runId, ledgerFailure);
        }
    }

    private MemorySnapshot loadMemory(ActorId actorId) {
        try {
            return memoryUseCase.recall(actorId);
        } catch (Exception e) {
            log.warn("에이전트 메모리 로드 실패 actor={}", actorId.value(), e);
            return MemorySnapshot.EMPTY;
        }
    }

    static String modalityGuidance(AgentModality modality) {
        return AgentConversationPrompt.modalityGuidance(modality);
    }

    static boolean usesSharedActorMemory(String sessionKey) {
        return AgentConversationPrompt.usesSharedActorMemory(sessionKey);
    }

    static String sanitizeFinalResponse(String value) {
        return AgentFinalResponseSanitizer.sanitize(value);
    }
}
