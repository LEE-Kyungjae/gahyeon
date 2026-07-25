package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AgentToolPolicyTest {
    @Test
    void unknownToolsFailClosed() {
        AgentToolPolicy policy = new AgentToolPolicy();

        assertThat(policy.decide(AgentGateway.TEXT, "invented_tool"))
                .isEqualTo(AgentToolDecision.DENY);
    }

    @Test
    void writeToolsRequireApprovalAndDestructiveToolsAreDenied() {
        AgentToolPolicy policy = new AgentToolPolicy(Map.of(
                "write_calendar", AgentToolRisk.WRITE,
                "delete_everything", AgentToolRisk.DESTRUCTIVE));

        assertThat(policy.decide(AgentGateway.TEXT, "write_calendar"))
                .isEqualTo(AgentToolDecision.REQUIRE_APPROVAL);
        assertThat(policy.decide(AgentGateway.VOICE, "write_calendar"))
                .isEqualTo(AgentToolDecision.REQUIRE_APPROVAL);
        assertThat(policy.decide(AgentGateway.TEXT, "delete_everything"))
                .isEqualTo(AgentToolDecision.DENY);
    }
}
