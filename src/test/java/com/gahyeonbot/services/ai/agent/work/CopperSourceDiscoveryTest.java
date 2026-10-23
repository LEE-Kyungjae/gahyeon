package com.gahyeonbot.services.ai.agent.work;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class CopperSourceDiscoveryTest {
    @Test void originalCopperIntentDiscoversDatedTableWithoutTrustingSearchRankOrModelQuery() {
        var session=new WebResearchSession(url -> new PublicWebClient.Page(url,"text/plain","Dated cash settlement and three month table fixture."),"LME 구리 일간가격 검색");
        var tools=session.tools();
        String discovered=tools.getFirst().call("{\"query\":\"model-injected-secret\"}");
        assertThat(discovered).contains("discovery_only","UNVERIFIED_DISCOVERY","field=LME_Cu_cash")
                .doesNotContain("model-injected-secret");
        assertThat(tools.get(1).call("{\"url\":\"https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash\"}"))
                .contains("source_read");
        assertThat(tools.getFirst().call("{\"query\":\"different model query\"}"))
                .contains("search_already_completed");
    }
}
