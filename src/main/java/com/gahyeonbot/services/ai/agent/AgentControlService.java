package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentRunRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AgentControlService {
    private final AgentRunRepository runRepository;
    private final AgentApprovalService approvalService;
    private final AgentRunLedger ledger;
    private final AgentRuntime runtime;

    @Transactional(readOnly = true)
    public AgentRunView latest(long actorUserId) {
        AgentRun run = runRepository.findFirstByUserIdOrderByCreatedAtDesc(actorUserId)
                .orElseThrow(() -> new IllegalArgumentException("에이전트 실행 기록이 없습니다."));
        return view(run, actorUserId);
    }

    @Transactional(readOnly = true)
    public AgentRunView get(String runId, long actorUserId) {
        AgentRun run = owned(runId, actorUserId);
        return view(run, actorUserId);
    }

    public AgentResult approveAndResume(String approvalId, long actorUserId) {
        var approval = approvalService.decide(approvalId, actorUserId, true);
        ledger.appendToolEvent(approval.getRun().getId(), AgentEventType.APPROVAL_RESOLVED,
                approval.getToolName(), "approved by " + actorUserId);
        return runtime.resume(approval.getRun().getId(), actorUserId);
    }

    public AgentRunView reject(String approvalId, long actorUserId) {
        var approval = approvalService.decide(approvalId, actorUserId, false);
        String runId = approval.getRun().getId();
        ledger.appendToolEvent(runId, AgentEventType.APPROVAL_RESOLVED,
                approval.getToolName(), "rejected by " + actorUserId);
        AgentRun cancelled = ledger.cancel(runId, actorUserId, "approval rejected");
        return view(cancelled, actorUserId);
    }

    public AgentRunView cancel(String runId, long actorUserId) {
        return view(ledger.cancel(runId, actorUserId, "cancelled by user"), actorUserId);
    }

    private AgentRun owned(String runId, long actorUserId) {
        AgentRun run = runRepository.findById(runId)
                .orElseThrow(() -> new IllegalArgumentException("실행을 찾을 수 없습니다: " + runId));
        if (run.getUserId() != actorUserId) {
            throw new SecurityException("이 실행을 조회할 권한이 없습니다.");
        }
        return run;
    }

    private AgentRunView view(AgentRun run, long actorUserId) {
        var approvals = approvalService.list(run.getId(), actorUserId).stream()
                .map(value -> new AgentRunView.ApprovalView(
                        value.getId(), value.getToolName(), value.getStatus()))
                .toList();
        return new AgentRunView(
                run.getId(),
                run.getStatus(),
                run.getCurrentStep(),
                run.getMaxSteps(),
                run.getInputText(),
                run.getOutputText(),
                run.getErrorCode(),
                run.getUpdatedAt(),
                approvals);
    }
}
