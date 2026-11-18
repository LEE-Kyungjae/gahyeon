package com.gahyeonbot.services.ai.agent;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;

import java.time.Duration;
import java.util.Locale;

/**
 * 에이전트 실행 결과별 횟수와 소요 시간을 기록한다.
 */
final class AgentRunMetrics {
    private final MeterRegistry meterRegistry;

    AgentRunMetrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    void record(AgentModality modality, String status, Duration duration) {
        meterRegistry.counter("gahyeonbot.agent.runs",
                "modality", modality.name().toLowerCase(Locale.ROOT),
                "status", status).increment();
        Timer.builder("gahyeonbot.agent.run.duration")
                .tag("modality", modality.name().toLowerCase(Locale.ROOT))
                .tag("status", status)
                .register(meterRegistry)
                .record(duration);
    }
}
