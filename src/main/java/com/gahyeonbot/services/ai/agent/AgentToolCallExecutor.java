package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.core.tool.ToolDecision;
import com.gahyeonbot.core.tool.ToolPolicy;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.tool.ToolCallback;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static com.gahyeonbot.services.ai.agent.AgentCancellation.ensureNotCancelled;
import static com.gahyeonbot.services.ai.agent.AgentEventPayloads.limited;

/**
 * 모델이 요청한 도구 호출을 정책·승인 경계를 거쳐 실행하고 원장에 기록한다.
 * 한 실행(run)의 수명 동안 하나의 인스턴스를 쓴다.
 */
final class AgentToolCallExecutor {
    private final AgentRunLedger ledger;
    private final ToolPolicy toolPolicy;
    private final AgentApprovalService approvalService;
    private final Map<String, ToolCallback> callbackByName;
    private final AgentLoopGuard loopGuard;

    AgentToolCallExecutor(
            AgentRunLedger ledger,
            ToolPolicy toolPolicy,
            AgentApprovalService approvalService,
            Map<String, ToolCallback> callbackByName,
            AgentLoopGuard loopGuard) {
        this.ledger = ledger;
        this.toolPolicy = toolPolicy;
        this.approvalService = approvalService;
        this.callbackByName = callbackByName;
        this.loopGuard = loopGuard;
    }

    List<ToolResponseMessage.ToolResponse> executeAll(
            String runId,
            List<AssistantMessage.ToolCall> toolCalls,
            AgentStreamObserver streamObserver,
            AgentExecutionControl control,
            List<String> usedTools) throws Exception {
        List<ToolResponseMessage.ToolResponse> toolResponses = new ArrayList<>();
        for (AssistantMessage.ToolCall toolCall : toolCalls) {
            ensureNotCancelled(streamObserver, control);
            loopGuard.recordToolCall(toolCall.name(), toolCall.arguments());
            ToolCallback callback = callbackByName.get(toolCall.name());
            if (callback == null) {
                throw new IllegalStateException("등록되지 않은 도구입니다: " + toolCall.name());
            }
            ToolDecision decision = toolPolicy.decide(toolCall.name());
            ledger.appendToolEvent(runId, AgentEventType.TOOL_CALL_REQUESTED,
                    toolCall.name(), limited(toolCall.arguments()));
            if (decision == ToolDecision.DENY) {
                throw new IllegalStateException("정책상 허용되지 않은 도구입니다: " + toolCall.name());
            }
            if (decision == ToolDecision.REQUIRE_APPROVAL) {
                requireApproval(runId, toolCall);
            }

            if (!control.tryStartSideEffect()) {
                throw new AgentStreamCancelledException();
            }
            ledger.appendToolEvent(
                    runId, AgentEventType.TOOL_CALL_STARTED, toolCall.name(), null);
            String toolResult;
            try {
                toolResult = callback.call(toolCall.arguments());
            } catch (Exception toolFailure) {
                ledger.appendToolEvent(runId, AgentEventType.TOOL_CALL_FAILED,
                        toolCall.name(), limited(toolFailure.getMessage()));
                throw toolFailure;
            }
            ensureNotCancelled(streamObserver, control);
            ledger.appendToolEvent(runId, AgentEventType.TOOL_CALL_COMPLETED,
                    toolCall.name(), limited(toolResult));
            usedTools.add(toolCall.name());
            toolResponses.add(new ToolResponseMessage.ToolResponse(
                    toolCall.id(), toolCall.name(), toolResult));
        }
        return toolResponses;
    }

    private void requireApproval(String runId, AssistantMessage.ToolCall toolCall) {
        if (approvalService.consumeIfApproved(
                runId, toolCall.name(), toolCall.arguments())) {
            ledger.appendToolEvent(runId, AgentEventType.APPROVAL_CONSUMED,
                    toolCall.name(), limited(toolCall.arguments()));
            return;
        }
        var approval = approvalService.request(
                runId, toolCall.name(), toolCall.arguments());
        ledger.transition(runId, AgentRunStatus.WAITING_APPROVAL,
                AgentEventType.APPROVAL_REQUESTED, approval.getId());
        throw new AgentApprovalRequiredException(
                runId, toolCall.name(), toolCall.arguments());
    }
}
