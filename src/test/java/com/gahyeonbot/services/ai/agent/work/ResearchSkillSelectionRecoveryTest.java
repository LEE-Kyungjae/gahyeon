package com.gahyeonbot.services.ai.agent.work;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.services.ai.agent.*;
import com.gahyeonbot.services.ai.agent.skills.*;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
class ResearchSkillSelectionRecoveryTest {
    @Test void unknownVersionReturnsChoicesWithoutGrantingOrSelectingAnything() {
        var entries=new ArrayList<AgentSkillJournal.Entry>();
        var journal=new AgentSkillJournal() {
            public List<Entry> read(String id) { return List.copyOf(entries); }
            public void append(String id,Entry entry) { entries.add(entry); }
        };
        var request=new AgentRequest("qa","qa",AgentModality.TEXT,null,new ActorId(42),"qa","LME 구리 가격",8);
        var harness=new AgentSkillHarness("qa",42,null,new AgentSkillCatalog(),
                new AgentToolRegistry(new WebResearchTools(true).bindings(request)),journal);
        var selection=Arrays.stream(harness.callbacks()).filter(c -> c.getToolDefinition().name().equals("agent_skill_select")).findFirst().orElseThrow();
        assertThat(selection.call("{\"id\":\"web-research\",\"version\":\"99.0.0\"}"))
                .contains("invalid_skill_selection","1.0.0").doesNotContain("owner-workspace");
        assertThat(entries).isEmpty();
        assertThat(selection.call("{\"id\":\"web-research\",\"version\":\"1.0.0\"}"))
                .contains("research_read");
        assertThat(entries).hasSize(1);
    }
}
