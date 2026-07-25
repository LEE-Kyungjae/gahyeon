package com.gahyeonbot.services.ai.agent;

import com.gahyeonbot.entity.AgentBackgroundJob;
import com.gahyeonbot.entity.AgentRun;
import com.gahyeonbot.repository.AgentBackgroundJobRepository;
import com.gahyeonbot.repository.AgentRunRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Optional;
import java.util.UUID;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AgentBackgroundQueue {
    private final AgentBackgroundJobRepository jobRepository;
    private final AgentRunRepository runRepository;
    private final AgentRunLedger ledger;

    @Transactional
    public AgentBackgroundJob schedule(
            String runId, String jobType, String payload, Duration delay, int maxAttempts) {
        AgentRun run = runRepository.findById(runId)
                .orElseThrow(() -> new IllegalArgumentException("실행을 찾을 수 없습니다: " + runId));
        if (run.getStatus() != AgentRunStatus.RUNNING) {
            throw new IllegalStateException("RUNNING 실행만 백그라운드 대기로 전환할 수 있습니다.");
        }
        LocalDateTime now = LocalDateTime.now();
        AgentBackgroundJob job = jobRepository.save(AgentBackgroundJob.builder()
                .id(UUID.randomUUID().toString())
                .run(run)
                .jobType(jobType)
                .payload(payload == null ? "" : payload)
                .status(AgentBackgroundJobStatus.PENDING)
                .availableAt(now.plus(delay == null ? Duration.ZERO : delay))
                .attempts(0)
                .maxAttempts(Math.max(1, maxAttempts))
                .createdAt(now)
                .updatedAt(now)
                .build());
        ledger.transition(runId, AgentRunStatus.WAITING_BACKGROUND,
                AgentEventType.BACKGROUND_WAIT_STARTED, job.getId());
        return job;
    }

    @Transactional
    public Optional<AgentBackgroundClaim> claimDue() {
        LocalDateTime now = LocalDateTime.now();
        var job = jobRepository
                .findFirstByStatusAndAvailableAtLessThanEqualOrderByAvailableAtAsc(
                        AgentBackgroundJobStatus.PENDING, now);
        job.ifPresent(value -> {
            value.setStatus(AgentBackgroundJobStatus.RUNNING);
            value.setAttempts(value.getAttempts() + 1);
            value.setLockedAt(now);
            value.setUpdatedAt(now);
        });
        return job.map(value -> new AgentBackgroundClaim(
                value.getId(),
                value.getRun().getId(),
                value.getJobType(),
                value.getPayload()));
    }

    @Transactional
    public void complete(String jobId) {
        AgentBackgroundJob job = required(jobId);
        job.setStatus(AgentBackgroundJobStatus.SUCCEEDED);
        job.setCompletedAt(LocalDateTime.now());
        job.setUpdatedAt(LocalDateTime.now());
    }

    @Transactional
    public void retryOrFail(String jobId, String error) {
        AgentBackgroundJob job = required(jobId);
        job.setLastError(error);
        job.setLockedAt(null);
        job.setUpdatedAt(LocalDateTime.now());
        if (job.getRun().getStatus().terminal()) {
            job.setStatus(AgentBackgroundJobStatus.FAILED);
            job.setCompletedAt(LocalDateTime.now());
        } else if (job.getAttempts() >= job.getMaxAttempts()) {
            job.setStatus(AgentBackgroundJobStatus.FAILED);
            job.setCompletedAt(LocalDateTime.now());
            ledger.fail(job.getRun().getId(), "BACKGROUND_JOB_FAILED", error);
        } else {
            job.setStatus(AgentBackgroundJobStatus.PENDING);
            job.setAvailableAt(LocalDateTime.now().plusSeconds(5L * job.getAttempts()));
        }
    }

    @Transactional
    public int recoverStaleClaims(Duration staleAfter) {
        LocalDateTime cutoff = LocalDateTime.now().minus(staleAfter);
        List<AgentBackgroundJob> stale = jobRepository.findByStatusAndLockedAtBefore(
                AgentBackgroundJobStatus.RUNNING, cutoff);
        for (AgentBackgroundJob job : stale) {
            job.setStatus(AgentBackgroundJobStatus.PENDING);
            job.setLockedAt(null);
            job.setAvailableAt(LocalDateTime.now());
            job.setLastError("worker restart recovery");
            job.setUpdatedAt(LocalDateTime.now());
        }
        return stale.size();
    }

    private AgentBackgroundJob required(String jobId) {
        return jobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("백그라운드 작업을 찾을 수 없습니다."));
    }
}
