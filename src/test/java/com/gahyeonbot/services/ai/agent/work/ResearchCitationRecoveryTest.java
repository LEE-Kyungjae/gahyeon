package com.gahyeonbot.services.ai.agent.work;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.services.ai.agent.*;
import com.gahyeonbot.services.ai.agent.skills.*;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.assertj.core.api.Assertions.*;

class ResearchCitationRecoveryTest {
    @Test void invalidQuoteIsRecoverableButNeverSatisfiesEvidence() throws Exception {
        var json=new ObjectMapper();String url="https://example.com/table";
        var session=new WebResearchSession(u->new PublicWebClient.Page(u,"text/html","<p>16 October 2026 copper 14595.00 USD</p>"),url);
        session.read(json.readTree("{\"url\":\""+url+"\"}"));
        var invalid=session.verify(json.readTree("{\"citations\":[{\"url\":\""+url+"\",\"quote\":\"Fabricated price 999.00\"}]}"));
        assertThat(json.valueToTree(invalid).path("status").asText()).isEqualTo("citation_mismatch");
        var entries=new ArrayList<AgentSkillJournal.Entry>();
        var journal=new AgentSkillJournal() {
            public List<Entry> read(String id){return List.copyOf(entries);}
            public void append(String id,Entry e){entries.add(e);}
        };
        var request=new AgentRequest("qa","qa",AgentModality.TEXT,null,new ActorId(42),"qa","LME 구리 가격",8);
        var h=new AgentSkillHarness("qa",42,null,new AgentSkillCatalog(),new AgentToolRegistry(new WebResearchTools(true).bindings(request)),journal);
        h.select("web-research","1.0.0");
        h.beforeCall("research_verify");h.completed("research_verify",json.writeValueAsString(invalid));
        assertThat(h.missingEvidence()).contains("research_verify");
        var valid=session.verify(json.readTree("{\"citations\":[{\"url\":\""+url+"\",\"quote\":\"16 October 2026 copper 14595.00 USD\"}]}"));
        h.beforeCall("research_verify");h.completed("research_verify",json.writeValueAsString(valid));
        assertThat(h.missingEvidence()).doesNotContain("research_verify").contains("research_read");
    }
}
