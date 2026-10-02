package com.gahyeonbot.adapters.unreal;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class UnrealRuntimeMetricsVisemeSourceTest {
    @Test
    void preservesWaveformGuidedAsAnExplicitNonProviderSource() {
        var registry = new SimpleMeterRegistry();
        var metrics = new UnrealRuntimeMetrics(registry);

        metrics.visemeTimeline("waveform-guided");
        metrics.visemeAlignment("waveform-guided", "success", 1_000);

        assertThat(registry.get("gahyeon.unreal.viseme.timeline")
                .tag("source", "waveform-guided").counter().count()).isEqualTo(1);
        assertThat(registry.get("gahyeon.unreal.viseme.alignment")
                .tag("source", "waveform-guided").tag("result", "success").timer().count())
                .isEqualTo(1);
    }
}
