package com.gahyeonbot.application.world;

import com.gahyeonbot.adapters.world.WorldRuntimeHealthIndicator;
import com.gahyeonbot.core.world.WorldStateUseCase;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class WorldRuntimeLifeConditionTest {
    private final ApplicationContextRunner context = new ApplicationContextRunner()
            .withBean(WorldStateUseCase.class, () -> mock(WorldStateUseCase.class))
            .withUserConfiguration(
                    WorldRuntimeReadiness.class,
                    WorldStateRecoveryCoordinator.class,
                    WorldRuntimeHealthIndicator.class);

    @Test
    void lifeLoopCanStartWithoutEnablingBehaviorExecution() {
        context.withPropertyValues(
                        "gahyeon.life.enabled=true",
                        "gahyeon.behavior.enabled=false")
                .run(result -> {
                    assertThat(result).hasSingleBean(WorldRuntimeReadiness.class);
                    assertThat(result).hasSingleBean(WorldStateRecoveryCoordinator.class);
                    assertThat(result).hasSingleBean(WorldRuntimeHealthIndicator.class);
                });
    }

    @Test
    void behaviorRuntimeStillCreatesTheSharedReadinessGate() {
        context.withPropertyValues(
                        "gahyeon.life.enabled=false",
                        "gahyeon.behavior.enabled=true")
                .run(result -> {
                    assertThat(result).hasSingleBean(WorldRuntimeReadiness.class);
                    assertThat(result).hasSingleBean(WorldStateRecoveryCoordinator.class);
                    assertThat(result).hasSingleBean(WorldRuntimeHealthIndicator.class);
                });
    }

    @Test
    void dormantRuntimeDoesNotCreateAutonomousInfrastructure() {
        context.withPropertyValues(
                        "gahyeon.life.enabled=false",
                        "gahyeon.behavior.enabled=false")
                .run(result -> {
                    assertThat(result).doesNotHaveBean(WorldRuntimeReadiness.class);
                    assertThat(result).doesNotHaveBean(WorldStateRecoveryCoordinator.class);
                    assertThat(result).doesNotHaveBean(WorldRuntimeHealthIndicator.class);
                });
    }
}
