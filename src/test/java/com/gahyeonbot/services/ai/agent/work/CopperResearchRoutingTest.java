package com.gahyeonbot.services.ai.agent.work;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.tool.ToolDecision;
import com.gahyeonbot.services.ai.agent.*;
import com.gahyeonbot.services.ai.agent.skills.*;
import org.junit.jupiter.api.Test;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.assertj.core.api.Assertions.*;

class CopperResearchRoutingTest {
    @Test void copperSelectsResearchAuthorityWithoutRemovingPreviouslyAdvertisedTools() {
        var entries=new ArrayList<AgentSkillJournal.Entry>();
        var journal=new AgentSkillJournal() {
            public List<Entry> read(String id) { return List.copyOf(entries); }
            public void append(String id,Entry e) { entries.add(e); }
        };
        var factory=new AgentSkillHarnessFactory(new AgentSkillCatalog(),journal,List.of(),true);
        ReflectionTestUtils.setField(factory,"requestTools",List.of(new WebResearchTools(true)));
        var request=new AgentRequest("qa","qa",AgentModality.TEXT,null,new ActorId(42),"qa","LME 구리 일간가격",8);
        var harness=factory.open("qa",request,new ToolCallback[0],new com.gahyeonbot.core.tool.ToolPolicy());
        assertThat(harness.callbacks()).extracting(c->c.getToolDefinition().name())
                .containsExactly("agent_skill_select","research_search","research_read","research_verify");
        harness.beforeCall("research_search"); harness.completed("research_search","{\"status\":\"discovery_only\"}");
        assertThat(harness.callbacks()).extracting(c->c.getToolDefinition().name())
                .containsExactly("agent_skill_select","research_search","research_read","research_verify");
        assertThat(harness.missingEvidence()).contains("research_read","research_verify");
        var replay=factory.open("qa",request,new ToolCallback[0],new com.gahyeonbot.core.tool.ToolPolicy());
        assertThat(replay.callbacks()).extracting(c->c.getToolDefinition().name()).contains("research_search");
    }
}
