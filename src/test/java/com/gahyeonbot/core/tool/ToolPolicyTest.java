package com.gahyeonbot.core.tool;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class ToolPolicyTest {
    @Test
    void allowsTheReadOnlyRecentNewsTool() {
        assertThat(new ToolPolicy().decide("get_recent_personalized_news"))
                .isEqualTo(ToolDecision.ALLOW);
    }

    @Test
    void unknownToolsFailClosed() {
        ToolPolicy policy = new ToolPolicy();

        assertThat(policy.decide("invented_tool"))
                .isEqualTo(ToolDecision.DENY);
    }

    @Test
    void writeToolsRequireApprovalAndDestructiveToolsAreDenied() {
        ToolPolicy policy = new ToolPolicy(Map.of(
                "write_calendar", ToolRisk.WRITE,
                "delete_everything", ToolRisk.DESTRUCTIVE));

        assertThat(policy.decide("write_calendar"))
                .isEqualTo(ToolDecision.REQUIRE_APPROVAL);
        assertThat(policy.decide("delete_everything"))
                .isEqualTo(ToolDecision.DENY);
    }
}
