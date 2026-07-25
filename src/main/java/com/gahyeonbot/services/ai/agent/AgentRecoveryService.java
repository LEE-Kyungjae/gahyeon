package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.repository.AgentRunRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
@Slf4j
public class AgentRecoveryService {
    private static final Duration STALE_AFTER = Duration.ofMinutes(15);

    private final AgentRunRepository runRepository;
    private final AgentRunLedger ledger;
    private final AgentBackgroundQueue backgroundQueue;

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        recover();
    }

    @Scheduled(fixedDelayString = "${agent.recovery.poll-millis:60000}")
    public void recover() {
        int jobs = backgroundQueue.recoverStaleClaims(STALE_AFTER);
        int runs = 0;
        for (var run : runRepository.findByStatusAndUpdatedAtBefore(
                AgentRunStatus.RUNNING, LocalDateTime.now().minus(STALE_AFTER))) {
            try {
                ledger.fail(run.getId(), "INTERRUPTED_OR_STALE",
                        "에이전트 실행이 장시간 갱신되지 않아 안전하게 종료되었습니다.");
                runs++;
            } catch (Exception e) {
                log.warn("stale agent run 복구 실패 run={}", run.getId(), e);
            }
        }
        if (jobs > 0 || runs > 0) {
            log.info("에이전트 복구 완료 backgroundJobs={}, staleRuns={}", jobs, runs);
        }
    }
}
