package com.gahyeonbot.services.ai.agent.work;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class ResearchUnavailableSourceTest {
    @Test void unavailablePageDoesNotDiscardOtherEvidenceOrRelaxSecurity() throws Exception {
        var json = new ObjectMapper();
        var session = new WebResearchSession(url -> {
            if (url.endsWith("unavailable")) throw new IllegalStateException("Source unavailable");
            return new PublicWebClient.Page(url,"text/plain","Published copper cash settlement 14539 USD per tonne.");
        }, "https://www.lme.com/unavailable https://www.nonferrous.or.kr/available");
        var read=session.tools().get(1);
        assertThat(read.call("{\"url\":\"https://www.lme.com/unavailable\"}"))
                .contains("source_unavailable").doesNotContain("source_read");
        assertThat(read.call("{\"url\":\"https://www.nonferrous.or.kr/available\"}"))
                .contains("source_read");
        assertThatThrownBy(() -> read.call("{\"url\":\"https://127.0.0.1/private\"}"))
                .isInstanceOf(SecurityException.class);
        assertThat(session.tools().get(2).call("{\"citations\":[{\"url\":\"https://www.lme.com/unavailable\",\"quote\":\"invented copper cash settlement\"}]}"))
                .contains("citation_mismatch").doesNotContain("citations_checked");
    }
}
