package com.gahyeonbot.services.ai.agent.skills;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.repository.AgentRunEventRepository;
import com.gahyeonbot.services.ai.agent.AgentEventType;
import com.gahyeonbot.services.ai.agent.AgentRunLedger;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public final class LedgerAgentSkillJournal implements AgentSkillJournal {
    private final AgentRunEventRepository events;
    private final AgentRunLedger ledger;
    private final ObjectMapper json;

    public LedgerAgentSkillJournal(AgentRunEventRepository events, AgentRunLedger ledger, ObjectMapper json) {
        this.events = events;
        this.ledger = ledger;
        this.json = json;
    }

    @Override public List<Entry> read(String runId) {
        return events.findByRunIdOrderBySequenceAsc(runId).stream()
                .filter(event -> event.getEventType() == AgentEventType.SKILL_EXECUTION_RECORDED)
                .map(event -> {
                    try { return json.readValue(event.getPayload(), Entry.class); }
                    catch (java.io.IOException failure) {
                        throw new IllegalStateException("Corrupt skill execution journal", failure);
                    }
                }).toList();
    }

    @Override public void append(String runId, Entry entry) {
        try {
            ledger.appendToolEvent(runId, AgentEventType.SKILL_EXECUTION_RECORDED,
                    entry.tool(), json.writeValueAsString(entry));
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot encode skill execution journal", failure);
        }
    }
}
