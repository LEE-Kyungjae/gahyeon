package com.gahyeonbot.services.ai.agent;

import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Pure assessment; not a declaration that the user's entire task was fulfilled. */
public final class AgentTaskEvidencePolicy {
    public enum Outcome {
        NOT_REQUIRED, BLOCKED_CAPABILITY, MISSING_TOOL_ATTEMPT,
        TOOL_FAILED, NO_DATA, EVIDENCE_AVAILABLE
    }
    public enum ToolOutcome { FAILED, EMPTY, EVIDENCE }
    public record Requirement(Set<String> acceptedTools) {
        public Requirement { acceptedTools = Set.copyOf(acceptedTools); }
        public static Requirement recentNews() {
            return new Requirement(Set.of("get_recent_personalized_news"));
        }
    }
    public record ToolEvidence(String tool, ToolOutcome outcome) {
        public ToolEvidence {
            Objects.requireNonNull(tool);
            Objects.requireNonNull(outcome);
        }
    }
    public record Assessment(Outcome outcome, boolean retryToolSelection) {}

    public Assessment assess(Requirement requirement, Set<String> allowedRegisteredTools,
                             List<ToolEvidence> attempts, int correctionAttempts, int remainingSteps) {
        Objects.requireNonNull(requirement);
        Objects.requireNonNull(allowedRegisteredTools);
        Objects.requireNonNull(attempts);
        if (requirement.acceptedTools().isEmpty()) return new Assessment(Outcome.NOT_REQUIRED, false);
        Set<String> accepted = requirement.acceptedTools();
        List<ToolEvidence> relevant = attempts.stream()
                .filter(attempt -> accepted.contains(attempt.tool()))
                .filter(attempt -> allowedRegisteredTools.contains(attempt.tool()))
                .toList();
        // Completed evidence remains usable if dynamic tool selection later changes its catalogue.
        // Callers must supply all policy-authorized tools for the run, not just the current model step.
        if (relevant.stream().anyMatch(attempt -> attempt.outcome() == ToolOutcome.EVIDENCE)) {
            return new Assessment(Outcome.EVIDENCE_AVAILABLE, false);
        }
        if (accepted.stream().noneMatch(allowedRegisteredTools::contains)) {
            return new Assessment(Outcome.BLOCKED_CAPABILITY, false);
        }
        if (relevant.isEmpty()) {
            return new Assessment(Outcome.MISSING_TOOL_ATTEMPT,
                    correctionAttempts == 0 && remainingSteps >= 2);
        }
        if (relevant.stream().anyMatch(attempt -> attempt.outcome() == ToolOutcome.EMPTY)) {
            return new Assessment(Outcome.NO_DATA, false);
        }
        return new Assessment(Outcome.TOOL_FAILED, false);
    }
}
