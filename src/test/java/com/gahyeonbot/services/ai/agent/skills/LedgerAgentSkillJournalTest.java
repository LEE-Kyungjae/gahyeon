package com.gahyeonbot.services.ai.agent.skills;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.repository.AgentRunEventRepository;
import com.gahyeonbot.services.ai.agent.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.*;

@DataJpaTest
@Import(AgentRunLedger.class)
class LedgerAgentSkillJournalTest {
    @Autowired AgentRunLedger ledger;
    @Autowired AgentRunEventRepository events;

    @Test void roundTripsVersionAndEvidenceInExistingLedgerAndRejectsTerminalWrites() {
        var run = ledger.create(new AgentRunRequest("skill-journal", "session", AgentModality.TEXT,
                7L, new ActorId(42L), "fixture", "private user input", 8));
        ledger.transition(run.getId(), AgentRunStatus.RUNNING, AgentEventType.RUN_STARTED, null);
        var journal = new LedgerAgentSkillJournal(events, ledger, new ObjectMapper());
        var selected = new AgentSkillJournal.Entry("selected", "fixture", "1.0.0",
                AgentSkill.sha256("procedure"), null, null);
        journal.append(run.getId(), selected);
        var reopened = new LedgerAgentSkillJournal(events, ledger, new ObjectMapper());
        assertThat(reopened.read(run.getId())).containsExactly(selected);
        assertThat(reopened.read("another-run")).isEmpty();
        assertThat(events.findByRunIdOrderBySequenceAsc(run.getId()))
                .filteredOn(event -> event.getEventType() == AgentEventType.SKILL_EXECUTION_RECORDED)
                .allSatisfy(event -> assertThat(event.getPayload()).doesNotContain("private user input"));
        ledger.cancel(run.getId(), new ActorId(42L), "cancelled");
        assertThatThrownBy(() -> reopened.append(run.getId(), selected))
                .isInstanceOf(IllegalStateException.class).hasMessageContaining("종료된");
    }
}
