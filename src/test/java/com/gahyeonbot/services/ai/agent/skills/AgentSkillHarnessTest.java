package com.gahyeonbot.services.ai.agent.skills;

import com.gahyeonbot.core.tool.ToolDecision;
import org.junit.jupiter.api.Test;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.definition.ToolDefinition;

import java.util.*;

import static org.assertj.core.api.Assertions.*;

class AgentSkillHarnessTest {
    private static final String TOOL = "get_weather_forecast";

    @Test void releasedPackageHasProcedureAndStableIdentity() {
        var catalog = new AgentSkillCatalog();
        var skill = catalog.require("outing-weather", "1.0.0");
        assertThat(skill.instructions()).contains("예약", "실제로 해결");
        assertThat(skill.requiredEvidenceTools()).containsExactly(TOOL);
        assertThat(new AgentSkillCatalog().require(skill.id(), skill.version()).digest()).isEqualTo(skill.digest());
    }

    @Test void selectionNarrowsToolsAndCannotGrantNewAuthority() {
        var harness = harness(skill(2), new Journal(), ToolDecision.ALLOW);
        assertThat(harness.callbacks()).extracting(t -> t.getToolDefinition().name())
                .contains("unrelated_read");
        harness.select("fixture", "1.0.0");
        assertThat(harness.callbacks()).extracting(t -> t.getToolDefinition().name())
                .containsExactly(AgentSkillHarness.SELECT_TOOL, TOOL);
        assertThat(harness.decision("unrelated_read")).isEqualTo(ToolDecision.DENY);
        assertThatThrownBy(() -> harness.beforeCall("unrelated_read")).isInstanceOf(SecurityException.class);
    }

    @Test void cannotFinishFromModelClaimWithoutToolEvidence() {
        var journal = new Journal();
        var harness = harness(skill(2), journal, ToolDecision.ALLOW);
        harness.select("fixture", "1.0.0");
        assertThatThrownBy(harness::verifyCompletion).hasMessageContaining("evidence missing");
        harness.beforeCall(TOOL);
        harness.completed(TOOL, "private forecast result");
        harness.verifyCompletion();
        assertThat(journal.read("run")).extracting(AgentSkillJournal.Entry::kind)
                .containsExactly("selected", "attempt", "evidence", "verified");
        assertThat(journal.read("run").toString()).doesNotContain("private forecast result");
    }

    @Test void emptyOrFailedCallsCannotSupplyEvidenceAndAttemptsConsumeBudget() {
        var journal = new Journal();
        var harness = harness(skill(1), journal, ToolDecision.ALLOW);
        harness.select("fixture", "1.0.0");
        harness.beforeCall(TOOL);
        assertThatThrownBy(() -> harness.completed(TOOL, " ")).hasMessageContaining("Empty");
        assertThat(harness.missingEvidence()).containsExactly(TOOL);
        assertThatThrownBy(() -> harness.beforeCall(TOOL)).hasMessageContaining("budget exhausted");
        assertThatThrownBy(() -> harness(skill(1), journal, ToolDecision.ALLOW).beforeCall(TOOL))
                .hasMessageContaining("budget exhausted");
    }

    @Test void restartRestoresPinnedProcedureAndEvidenceButAnotherRunGetsNone() {
        var journal = new Journal();
        var first = harness(skill(2), journal, ToolDecision.ALLOW);
        first.select("fixture", "1.0.0");
        first.beforeCall(TOOL);
        first.completed(TOOL, "evidence");
        var resumed = harness(skill(2), journal, ToolDecision.ALLOW);
        assertThat(resumed.missingEvidence()).isEmpty();
        assertThat(resumed.guidance()).contains("fixture@1.0.0");
        resumed.verifyCompletion();
        var other = new AgentSkillHarness("other", 42L, 7L, new AgentSkillCatalog(List.of(skill(2))),
                registry(ToolDecision.ALLOW), journal);
        other.select("fixture", "1.0.0");
        assertThat(other.missingEvidence()).containsExactly(TOOL);
    }

    @Test void changedVersionContentCannotResumeSilently() {
        var journal = new Journal();
        var first = harness(skill(2), journal, ToolDecision.ALLOW);
        first.select("fixture", "1.0.0");
        var original = skill(2);
        var changed = new AgentSkill(original.id(), original.version(), original.problem(), original.whenToUse(),
                original.allowedTools(), original.requiredEvidenceTools(), 2, original.completionCriteria(),
                "changed", AgentSkill.sha256("changed"));
        assertThatThrownBy(() -> harness(changed, journal, ToolDecision.ALLOW)).hasMessageContaining("Pinned skill changed");
    }

    @Test void deniedDependencyCannotBeSelectedAndApprovalIsNotRemovedBySkill() {
        var denied = harness(skill(2), new Journal(), ToolDecision.DENY);
        assertThat(denied.guidance()).doesNotContain("fixture@");
        assertThatThrownBy(() -> denied.select("fixture", "1.0.0")).hasMessageContaining("unauthorized");
        var approval = harness(skill(2), new Journal(), ToolDecision.REQUIRE_APPROVAL);
        approval.select("fixture", "1.0.0");
        assertThat(approval.decision(TOOL)).isEqualTo(ToolDecision.REQUIRE_APPROVAL);
    }

    @Test void remoteToolNeedsSkillActorAndScopeAndRevocationBlocksResume() {
        var remote = new AgentToolRegistry(List.of(new AgentToolRegistry.Binding(
                "mcp:fixture", callback(TOOL), ToolDecision.ALLOW, Set.of(42L), 7L)));
        var catalog = new AgentSkillCatalog(List.of(skill(2)));
        var journal = new Journal();
        var authorized = new AgentSkillHarness("run", 42L, 7L, catalog, remote, journal);
        assertThat(authorized.decision(TOOL)).isEqualTo(ToolDecision.DENY);
        authorized.select("fixture", "1.0.0");
        assertThat(authorized.decision(TOOL)).isEqualTo(ToolDecision.ALLOW);
        assertThatThrownBy(() -> new AgentSkillHarness("run", 99L, 7L, catalog, remote, journal))
                .hasMessageContaining("unauthorized");
        var wrongScope = new AgentSkillHarness("other", 42L, 8L, catalog, remote, journal);
        assertThatThrownBy(() -> wrongScope.select("fixture", "1.0.0")).hasMessageContaining("unauthorized");
    }

    @Test void duplicateToolsAndUnscopedMcpGrantsFailClosed() {
        var binding = new AgentToolRegistry.Binding("native", callback(TOOL), ToolDecision.ALLOW, Set.of(), null);
        assertThatThrownBy(() -> new AgentToolRegistry(List.of(binding, binding))).hasMessageContaining("Duplicate");
        assertThatThrownBy(() -> new AgentToolRegistry.Binding("mcp:fixture", callback(TOOL),
                ToolDecision.ALLOW, Set.of(), null)).hasMessageContaining("explicit actor");
    }

    @Test void selectionIsIdempotentAndRejectsUnknownVersionsAndMalformedArguments() {
        var journal = new Journal();
        var harness = harness(skill(2), journal, ToolDecision.ALLOW);
        var callback = harness.callbacks()[0];
        assertThatThrownBy(() -> callback.call("{\"id\":\"fixture\"}")).hasMessageContaining("Invalid");
        assertThatThrownBy(() -> harness.select("fixture", "2.0.0")).hasMessageContaining("Unknown");
        callback.call("{\"id\":\"fixture\",\"version\":\"1.0.0\"}");
        harness.select("fixture", "1.0.0");
        assertThat(journal.read("run")).hasSize(1);
    }

    static AgentSkill skill(int budget) {
        return new AgentSkill("fixture", "1.0.0", "problem", "when", Set.of(TOOL), Set.of(TOOL),
                budget, List.of("check result"), "procedure", AgentSkill.sha256("fixture-" + budget));
    }

    private static AgentSkillHarness harness(AgentSkill skill, Journal journal, ToolDecision decision) {
        return new AgentSkillHarness("run", 42L, 7L, new AgentSkillCatalog(List.of(skill)), registry(decision), journal);
    }

    private static AgentToolRegistry registry(ToolDecision decision) {
        return new AgentToolRegistry(List.of(
                new AgentToolRegistry.Binding("native", callback(TOOL), decision, Set.of(), null),
                new AgentToolRegistry.Binding("native", callback("unrelated_read"), ToolDecision.ALLOW, Set.of(), null)));
    }

    static ToolCallback callback(String name) {
        return new ToolCallback() {
            @Override public ToolDefinition getToolDefinition() {
                return ToolDefinition.builder().name(name).description("fixture").inputSchema("{\"type\":\"object\"}").build();
            }
            @Override public String call(String input) { return "result"; }
        };
    }

    static class Journal implements AgentSkillJournal {
        private final Map<String, List<Entry>> entries = new HashMap<>();
        @Override public List<Entry> read(String runId) { return List.copyOf(entries.getOrDefault(runId, List.of())); }
        @Override public void append(String runId, Entry entry) { entries.computeIfAbsent(runId, key -> new ArrayList<>()).add(entry); }
    }
}
