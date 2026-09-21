package com.gahyeonbot.adapters.jev;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(JevProperties.class)
@ConditionalOnProperty(name = "gahyeon.jev.enabled", havingValue = "true")
public class JevConfiguration {
    @Bean
    JevDecisionClient jevDecisionClient(JevProperties properties, ObjectMapper mapper, MeterRegistry metrics) {
        return new JevDecisionClient(properties, mapper, metrics);
    }

    @Bean
    @ConditionalOnProperty(name = "gahyeon.jev.expression-enabled", havingValue = "true", matchIfMissing = true)
    JevExpressionModel jevExpressionModel(JevDecisionClient client, JevProperties properties) {
        return new JevExpressionModel(client, properties);
    }

    @Bean
    @ConditionalOnProperty(name = "gahyeon.jev.memory-enabled", havingValue = "true", matchIfMissing = true)
    JevMemoryReranker jevMemoryReranker(JevDecisionClient client, JevProperties properties) {
        return new JevMemoryReranker(client, properties);
    }
}
