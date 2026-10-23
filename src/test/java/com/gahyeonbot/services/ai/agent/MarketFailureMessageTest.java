package com.gahyeonbot.services.ai.agent;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class MarketFailureMessageTest {
    @Test void failedPriceLookupDoesNotClaimNewsWasRequested() {
        assertThat(new AgentLookupEvidence("LME 구리 일간가격 검색").fallback(AgentTaskEvidencePolicy.Outcome.TOOL_FAILED))
                .contains("시세").doesNotContain("뉴스","기사");
    }
}
