package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.adapters.speech.SileroVadDetector;
import com.gahyeonbot.application.speech.StreamingUtteranceAccumulator;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.env.SystemEnvironmentPropertySource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.Map;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.mock;

class VoiceAssistantVadSelectionTest {
    @Test void environmentSelectionReachesActualDiscordUtterance() throws Exception {
        var properties = properties(Map.of("ASSISTANT_VAD_PROVIDER", "silero",
                "ASSISTANT_VAD_MIN_SPEECH_MILLIS", "150", "ASSISTANT_VAD_THRESHOLD", "0.3"));
        assertThat(properties.getVad().getMinSpeechMillis()).isEqualTo(150);
        try (var accumulator = utterance(properties)) {
            assertThat(ReflectionTestUtils.getField(accumulator, "detector")).isInstanceOf(SileroVadDetector.class);
            accumulator.accept(new byte[192000], 0);
            assertThat(accumulator.poll(5000)).isEmpty();
        }
    }

    @Test void defaultProviderRemainsTen() throws Exception {
        assertThat(properties(Map.of()).getVad().getProvider()).isEqualTo("ten");
    }

    @Test void invalidSelectionCannotSilentlyDisableVad() throws Exception {
        var properties = properties(Map.of("ASSISTANT_VAD_PROVIDER", "sillero"));
        assertThatThrownBy(() -> utterance(properties)).hasCauseInstanceOf(IllegalArgumentException.class);
    }

    @Test void explicitlyDisabledVadDoesNotLoadAModel() throws Exception {
        var properties = properties(Map.of("ASSISTANT_VAD_ENABLED", "false",
                "ASSISTANT_VAD_PROVIDER", "silero", "ASSISTANT_VAD_SILERO_MODEL_PATH", "/missing/model.onnx"));
        try (var accumulator = utterance(properties)) {
            assertThat(ReflectionTestUtils.getField(accumulator, "detector")).isNull();
        }
    }

    private AssistantProperties properties(Map<String, Object> values) throws Exception {
        var environment = new StandardEnvironment();
        environment.getPropertySources().remove(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME);
        environment.getPropertySources().remove(StandardEnvironment.SYSTEM_PROPERTIES_PROPERTY_SOURCE_NAME);
        environment.getPropertySources().addFirst(new SystemEnvironmentPropertySource("test-environment", values));
        for (var source : new YamlPropertySourceLoader().load("application", new ClassPathResource("application.yml"))) {
            environment.getPropertySources().addLast(source);
        }
        return Binder.get(environment).bind("assistant", AssistantProperties.class).get();
    }

    private StreamingUtteranceAccumulator utterance(AssistantProperties properties) throws Exception {
        var service = mock(VoiceAssistantService.class);
        ReflectionTestUtils.setField(service, "properties", properties);
        var constructor = Class.forName(VoiceAssistantService.class.getName() + "$Utterance")
                .getDeclaredConstructor(VoiceAssistantService.class, String.class);
        constructor.setAccessible(true);
        Object utterance = constructor.newInstance(service, "synthetic-test");
        return (StreamingUtteranceAccumulator) ReflectionTestUtils.getField(utterance, "accumulator");
    }
}
