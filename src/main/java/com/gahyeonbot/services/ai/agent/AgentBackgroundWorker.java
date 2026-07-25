package com.gahyeonbot.services.ai.agent;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Component
@Slf4j
public class AgentBackgroundWorker {
    private final AgentBackgroundQueue queue;
    private final AgentRuntime runtime;
    private final Map<String, AgentBackgroundHandler> handlers;

    public AgentBackgroundWorker(
            AgentBackgroundQueue queue,
            AgentRuntime runtime,
            List<AgentBackgroundHandler> handlers) {
        this.queue = queue;
        this.runtime = runtime;
        this.handlers = handlers.stream().collect(Collectors.toUnmodifiableMap(
                AgentBackgroundHandler::jobType, Function.identity()));
    }

    @Scheduled(fixedDelayString = "${agent.background.poll-millis:1000}")
    public void poll() {
        queue.claimDue().ifPresent(job -> {
            AgentBackgroundHandler handler = handlers.get(job.jobType());
            if (handler == null) {
                queue.retryOrFail(job.jobId(), "등록되지 않은 background job type: " + job.jobType());
                return;
            }
            try {
                String result = handler.execute(job.payload());
                runtime.resumeBackground(job.runId(), result);
                queue.complete(job.jobId());
            } catch (Exception e) {
                log.warn("백그라운드 에이전트 작업 실패 job={}", job.jobId(), e);
                queue.retryOrFail(job.jobId(), limited(e.getMessage()));
            }
        });
    }

    private static String limited(String value) {
        if (value == null) return "unknown";
        return value.length() <= 2000 ? value : value.substring(0, 2000);
    }
}
