package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.entity.AgentApproval;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentApprovalRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@Import({AgentRunLedger.class, AgentApprovalService.class})
class AgentApprovalServiceTest {
    @Autowired AgentRunLedger ledger;
    @Autowired AgentApprovalService approvals;
    @Autowired AgentApprovalRepository approvalRepository;

    @Test
    void ownerCanApproveAndRuntimeConsumesExactlyOnce() {
        AgentRun run = waitingRun();
        AgentApproval request = approvals.request(run.getId(), "write_calendar", "{\"title\":\"회의\"}");

        approvals.decide(request.getId(), 1L, true);

        assertThat(approvals.consumeIfApproved(
                run.getId(), "write_calendar", "{\"title\":\"회의\"}")).isTrue();
        assertThat(approvals.consumeIfApproved(
                run.getId(), "write_calendar", "{\"title\":\"회의\"}")).isFalse();
        assertThat(approvalRepository.findById(request.getId()).orElseThrow().getStatus())
                .isEqualTo(AgentApprovalStatus.CONSUMED);
    }

    @Test
    void anotherUserCannotDecideApproval() {
        AgentRun run = waitingRun();
        AgentApproval request = approvals.request(run.getId(), "write_calendar", "{}");

        assertThatThrownBy(() -> approvals.decide(request.getId(), 999L, true))
                .isInstanceOf(SecurityException.class);
    }

    @Test
    void cancelRequiresRunOwner() {
        AgentRun run = waitingRun();

        assertThatThrownBy(() -> ledger.cancel(run.getId(), 999L, "no"))
                .isInstanceOf(SecurityException.class);
        assertThat(ledger.cancel(run.getId(), 1L, "user").getStatus())
                .isEqualTo(AgentRunStatus.CANCELLED);
    }

    private AgentRun waitingRun() {
        AgentRun run = ledger.create(new AgentRunRequest(
                "approval-" + java.util.UUID.randomUUID(),
                "text:1",
                AgentGateway.TEXT,
                10L,
                1L,
                "tester",
                "일정 등록",
                8));
        ledger.transition(run.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
        return ledger.transition(run.getId(), AgentRunStatus.WAITING_APPROVAL,
                AgentEventType.APPROVAL_REQUESTED, "test");
    }
}
