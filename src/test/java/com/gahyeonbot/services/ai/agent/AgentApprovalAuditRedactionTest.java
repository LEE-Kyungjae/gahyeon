package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.entity.AgentApproval;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentApprovalRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@Import({AgentRunLedger.class, AgentApprovalService.class})
class AgentApprovalAuditRedactionTest {
    @Autowired AgentRunLedger ledger;
    @Autowired AgentApprovalService approvals;
    @Autowired AgentApprovalRepository approvalRepository;

    @Test
    void persistsRedactedAuditArgumentsWithoutBreakingOriginalApprovalLookup() {
        AgentRun run = waitingRun();
        String original = "{\"path\":\"/Users/ze/private\",\"access_token\":\"live-secret\"}";

        AgentApproval request = approvals.request(run.getId(), "write_calendar", original);
        AgentApproval stored = approvalRepository.findById(request.getId()).orElseThrow();

        assertThat(stored.getToolArguments())
                .contains("[HOME]", "[REDACTED]")
                .doesNotContain("/Users/ze", "live-secret");

        approvals.decide(request.getId(), new ActorId(1L), true);
        assertThat(approvals.consumeIfApproved(run.getId(), "write_calendar", original)).isTrue();
    }

    private AgentRun waitingRun() {
        AgentRun run = ledger.create(new AgentRunRequest(
                "redaction-" + java.util.UUID.randomUUID(),
                "text:1",
                AgentModality.TEXT,
                10L,
                new ActorId(1L),
                "tester",
                "일정 등록",
                8));
        ledger.transition(run.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
        return ledger.transition(run.getId(), AgentRunStatus.WAITING_APPROVAL,
                AgentEventType.APPROVAL_REQUESTED, "test");
    }
}
