package com.gahyeonbot.adapters.jev;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.adapters.speech.SmallConversationExpressionModelConfiguration;
import com.gahyeonbot.application.speech.ConversationExpressionModel;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import static org.assertj.core.api.Assertions.assertThat;

/** Explicit local check: loads the private configuration but sends no provider requests. */
@EnabledIfEnvironmentVariable(named = "GAHYEON_JEV_LOCAL_CONFIG_CHECK", matches = "true")
class JevLocalConfigurationTest {
    @Test void loadsExternalCredentialAndRegistersRuntimeAdapters() {
        new ApplicationContextRunner().withInitializer(new ConfigDataApplicationContextInitializer())
                .withUserConfiguration(JevConfiguration.class, SmallConversationExpressionModelConfiguration.class)
                .withBean(ObjectMapper.class, ObjectMapper::new)
                .withBean(MeterRegistry.class, SimpleMeterRegistry::new)
                .withPropertyValues("spring.profiles.active=dev")
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    var properties = context.getBean(JevProperties.class);
                    assertThat(properties.isEnabled()).isTrue();
                    // Assert a boolean so assertion messages can never print a secret value.
                    assertThat(properties.getApiKey() != null && !properties.getApiKey().isBlank()).isTrue();
                    assertThat(context).hasSingleBean(ConversationExpressionModel.class);
                    assertThat(context.getBean(ConversationExpressionModel.class)).isInstanceOf(JevExpressionModel.class);
                    assertThat(context).hasSingleBean(JevMemoryReranker.class);
                });
    }
}
