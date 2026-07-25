package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentRunEventRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@Import(AgentRunLedger.class)
class AgentRunLedgerTest {
    @Autowired AgentRunLedger ledger;
    @Autowired AgentRunEventRepository eventRepository;

    @Test
    void persistsRunLifecycleAndOrderedEvents() {
        AgentRun created = ledger.create(request("discord-interaction-1"));
        AgentRun running = ledger.transition(
                created.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
        ledger.advanceStep(running.getId(), AgentEventType.MODEL_CALL_STARTED, "model=test");
        ledger.appendToolEvent(
                running.getId(), AgentEventType.TOOL_CALL_COMPLETED, "get_weather", "ok");
        AgentRun succeeded = ledger.succeed(running.getId(), "맑아");

        assertThat(succeeded.getStatus()).isEqualTo(AgentRunStatus.SUCCEEDED);
        assertThat(succeeded.getOutputText()).isEqualTo("맑아");
        assertThat(succeeded.getCurrentStep()).isEqualTo(1);
        assertThat(eventRepository.findByRunIdOrderBySequenceAsc(running.getId()))
                .extracting(event -> event.getEventType())
                .containsExactly(
                        AgentEventType.RUN_CREATED,
                        AgentEventType.RUN_STARTED,
                        AgentEventType.MODEL_CALL_STARTED,
                        AgentEventType.TOOL_CALL_COMPLETED,
                        AgentEventType.RUN_SUCCEEDED);
    }

    @Test
    void requestIdIsIdempotent() {
        AgentRun first = ledger.create(request("same-request"));
        AgentRun second = ledger.create(request("same-request"));

        assertThat(second.getId()).isEqualTo(first.getId());
        assertThat(eventRepository.findByRunIdOrderBySequenceAsc(first.getId())).hasSize(1);
    }

    @Test
    void rejectsInvalidTransition() {
        AgentRun run = ledger.create(request("invalid-transition"));

        assertThatThrownBy(() -> ledger.succeed(run.getId(), "no"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("QUEUED -> SUCCEEDED");
    }

    @Test
    void enforcesStepLimit() {
        AgentRun run = ledger.create(new AgentRunRequest(
                "step-limit", "text:1", AgentGateway.TEXT, 10L, 1L, "tester", "질문", 1));
        ledger.transition(run.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
        ledger.advanceStep(run.getId(), AgentEventType.MODEL_CALL_STARTED, null);

        assertThatThrownBy(() -> ledger.advanceStep(
                run.getId(), AgentEventType.MODEL_CALL_STARTED, null))
                .isInstanceOf(AgentRunLedger.StepLimitExceededException.class);
    }

    private static AgentRunRequest request(String requestId) {
        return new AgentRunRequest(
                requestId, "text:1", AgentGateway.TEXT, 10L, 1L, "tester", "날씨 알려줘", 8);
    }
}
