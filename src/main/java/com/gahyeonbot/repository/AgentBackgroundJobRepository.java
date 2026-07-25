package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentBackgroundJob;
import com.gahyeonbot.services.ai.agent.AgentBackgroundJobStatus;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.List;

public interface AgentBackgroundJobRepository extends JpaRepository<AgentBackgroundJob, String> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<AgentBackgroundJob>
    findFirstByStatusAndAvailableAtLessThanEqualOrderByAvailableAtAsc(
            AgentBackgroundJobStatus status, LocalDateTime now);

    List<AgentBackgroundJob> findByStatusAndLockedAtBefore(
            AgentBackgroundJobStatus status, LocalDateTime cutoff);
}
