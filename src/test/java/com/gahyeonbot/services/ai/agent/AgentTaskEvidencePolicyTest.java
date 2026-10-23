package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Set;
import static com.gahyeonbot.services.ai.agent.AgentTaskEvidencePolicy.*;
import static org.assertj.core.api.Assertions.assertThat;

class AgentTaskEvidencePolicyTest {
    private final AgentTaskEvidencePolicy policy = new AgentTaskEvidencePolicy();
    private final Requirement news = Requirement.recentNews();
    private final Set<String> available = Set.of("get_recent_personalized_news");

    @Test void deployedMissingNewsCapabilityIsBlockedRatherThanSuccessful() {
        assertThat(policy.assess(news, Set.of(), List.of(), 0, 4))
                .isEqualTo(new Assessment(Outcome.BLOCKED_CAPABILITY, false));
    }
    @Test void installedNewsToolMustBeAttemptedWithOneBoundedCorrection() {
        assertThat(policy.assess(news, available, List.of(), 0, 2))
                .isEqualTo(new Assessment(Outcome.MISSING_TOOL_ATTEMPT, true));
        assertThat(policy.assess(news, available, List.of(), 1, 4).retryToolSelection()).isFalse();
        assertThat(policy.assess(news, available, List.of(), 0, 1).retryToolSelection()).isFalse();
    }
    @Test void unrelatedWeatherCallCannotSatisfyNewsRequest() {
        assertThat(policy.assess(news, available,
                List.of(new ToolEvidence("get_current_weather", ToolOutcome.EVIDENCE)), 0, 4).outcome())
                .isEqualTo(Outcome.MISSING_TOOL_ATTEMPT);
    }
    @Test void toolCompletionDoesNotMeanDataWasFound() {
        assertThat(policy.assess(news, available,
                List.of(new ToolEvidence("get_recent_personalized_news", ToolOutcome.EMPTY)), 0, 4).outcome())
                .isEqualTo(Outcome.NO_DATA);
    }
    @Test void toolFailureIsSeparateFromMissingCapability() {
        assertThat(policy.assess(news, available,
                List.of(new ToolEvidence("get_recent_personalized_news", ToolOutcome.FAILED)), 0, 4).outcome())
                .isEqualTo(Outcome.TOOL_FAILED);
    }
    @Test void realEvidenceIsNotAutomaticallySemanticTaskSuccess() {
        assertThat(policy.assess(news, available,
                List.of(new ToolEvidence("get_recent_personalized_news", ToolOutcome.EVIDENCE)), 0, 4))
                .isEqualTo(new Assessment(Outcome.EVIDENCE_AVAILABLE, false));
    }
    @Test void unregisteredEvidenceCannotAuthorizeTools() {
        assertThat(policy.assess(news, Set.of(),
                List.of(new ToolEvidence("get_recent_personalized_news", ToolOutcome.EVIDENCE)), 0, 4).outcome())
                .isEqualTo(Outcome.BLOCKED_CAPABILITY);
    }
    @Test void ordinaryConversationDoesNotRequireTools() {
        assertThat(policy.assess(new Requirement(Set.of()), Set.of(), List.of(), 0, 4).outcome())
                .isEqualTo(Outcome.NOT_REQUIRED);
    }
    @Test void javaMethodNameIsNotTheRegisteredToolName() {
        assertThat(policy.assess(news, Set.of("getRecentPersonalizedNews"), List.of(), 0, 4).outcome())
                .isEqualTo(Outcome.BLOCKED_CAPABILITY);
    }
}
