package com.gahyeonbot.adapters.unreal;

import com.gahyeonbot.application.speech.StreamingExpressiveSpeechSynthesisPort;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class UnrealPcmStreamingConfigurationTest {

    @Test
    void doesNotRequireUnrealExecutorWhenWebsocketRuntimeIsDisabled() {
        new ApplicationContextRunner()
                .withUserConfiguration(UnrealPcmStreamingConfiguration.class)
                .withBean(StreamingExpressiveSpeechSynthesisPort.class,
                        () -> mock(StreamingExpressiveSpeechSynthesisPort.class))
                .withPropertyValues(
                        "gahyeon.headless.enabled=true",
                        "gahyeon.unreal.websocket.enabled=false")
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context).doesNotHaveBean(UnrealPcmStreamCache.class);
                });
    }
}
