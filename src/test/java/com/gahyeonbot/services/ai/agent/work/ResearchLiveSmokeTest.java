package com.gahyeonbot.services.ai.agent.work;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import java.nio.file.*;
import java.util.Map;
import java.util.List;
import static org.assertj.core.api.Assertions.*;

class ResearchLiveSmokeTest {
    @Test @EnabledIfEnvironmentVariable(named="GAHYEON_RESEARCH_LIVE_SMOKE", matches="true")
    void publicSearchAndPrimarySourceCanBeReadAndCited() throws Exception {
        var json = new ObjectMapper();
        var session = new WebResearchSession(new PublicWebClient()::get, "OpenSSH official manual https://www.openssh.com/manual.html");
        var tools = session.tools();
        var search = json.readTree(tools.getFirst().call("{\"query\":\"OpenSSH official manual\"}"));
        assertThat(search.path("results").size()).isGreaterThan(0);
        String url = "https://www.openssh.com/manual.html";
        var read = json.readTree(tools.get(1).call(json.writeValueAsString(Map.of("url",url))));
        url = read.path("source").path("url").asText();
        String text = read.path("source").path("text").asText();
        assertThat(text).contains("OpenSSH");
        String quote = text.substring(0, Math.min(80,text.length()));
        var verified = json.readTree(tools.get(2).call(json.writeValueAsString(Map.of("citations",List.of(Map.of("url",url,"quote",quote))))));
        assertThat(verified.path("status").asText()).isEqualTo("citations_checked");
        Path path = Path.of("artifacts/trusted-research-owner-work-20261016/live-research.json");
        Files.writeString(path,json.writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                "searchResultCount",search.path("results").size(),"sourceUrl",url,
                "authority",read.path("source").path("authority").asText(),
                "fetchedAt",read.path("source").path("fetchedAt").asText(),
                "verificationStatus",verified.path("status").asText(),"productionTraffic",false)));
    }
}
