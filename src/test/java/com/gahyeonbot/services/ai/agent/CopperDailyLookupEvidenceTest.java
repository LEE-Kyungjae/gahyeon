package com.gahyeonbot.services.ai.agent;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class CopperDailyLookupEvidenceTest {
    @Test void copperDailyPriceRequiresReadAndVerifiedEvidence() {
        var lookup=new AgentLookupEvidence("LME 구리 일간가격 검색해서 최신 거래일 가격 알려줘");
        assertThat(lookup.required()).isTrue();
        assertThat(lookup.intent()).isEqualTo("market");
        lookup.allow("research_verify");
        lookup.completed("research_search","{\"status\":\"discovery_only\"}");
        assertThat(lookup.assess(0).outcome()).isNotEqualTo(AgentTaskEvidencePolicy.Outcome.EVIDENCE_AVAILABLE);
        lookup.completed("research_verify","{\"status\":\"citations_checked\",\"citations\":[{\"url\":\"https://www.lme.com/\",\"quote\":\"cash settlement fixture\"}]}");
        assertThat(lookup.assess(0).outcome()).isEqualTo(AgentTaskEvidencePolicy.Outcome.EVIDENCE_AVAILABLE);
    }
}
