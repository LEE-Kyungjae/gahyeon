package com.gahyeonbot.services.ai.agent.work;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.services.ai.agent.*;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class DesktopResearchAvailabilityTest {
    @Test void desktopWithoutDiscordScopeCanResearchButCannotUseOwnerWork() {
        var request = new AgentRequest("desktop-lme", "desktop-qa", AgentModality.TEXT,
                null, new ActorId(42), "tester", "LME 구리 일간가격 검색", 10);
        var bindings = new WebResearchTools(true).bindings(request);
        assertThat(bindings).extracting(b -> b.name())
                .containsExactly("research_search", "research_read", "research_verify");
        assertThat(bindings).allSatisfy(b -> {
            assertThat(b.availableTo(42, null)).isTrue();
            assertThat(b.availableTo(43, null)).isFalse();
        });
        assertThat(new WebResearchTools(false).bindings(request)).isEmpty();
        var owner = new OwnerWorkTools(true, 42, 7, (target,input) -> {
            throw new AssertionError("Desktop research must not invoke remote work");
        });
        assertThat(owner.bindings(request)).isEmpty();
    }
}
