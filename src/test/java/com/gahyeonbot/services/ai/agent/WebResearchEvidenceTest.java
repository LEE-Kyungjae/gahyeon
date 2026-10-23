package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class WebResearchEvidenceTest {
    @Test void checkedWebCitationsSatisfyLookupEvidenceWithoutClaimingTruth() {
        var lookup = new AgentLookupEvidence("오늘 뉴스 찾아줘");
        lookup.allow("research_verify");
        lookup.completed("research_verify", "{\"status\":\"citations_checked\",\"truthVerified\":false,\"citations\":[{\"url\":\"https://example.com\",\"quote\":\"checked source\"}]}");
        assertThat(lookup.assess(0).outcome()).isEqualTo(AgentTaskEvidencePolicy.Outcome.EVIDENCE_AVAILABLE);
    }
    @Test void SearchSnippetsDoNotSatisfyLookupEvidence() {
        var lookup = new AgentLookupEvidence("오늘 뉴스 찾아줘");
        lookup.allow("research_verify");
        lookup.completed("research_search", "{\"status\":\"discovery_only\"}");
        lookup.completed("research_verify", "{\"status\":\"citations_checked\",\"citations\":[]}");
        assertThat(lookup.assess(0).outcome()).isEqualTo(AgentTaskEvidencePolicy.Outcome.TOOL_FAILED);
    }
}
