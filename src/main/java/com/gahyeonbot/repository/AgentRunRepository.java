package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentRun;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.time.LocalDateTime;

public interface AgentRunRepository extends JpaRepository<AgentRun, String> {
    Optional<AgentRun> findByRequestId(String requestId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from AgentRun r where r.id = :id")
    Optional<AgentRun> findByIdForUpdate(@Param("id") String id);

    @Query("select r from AgentRun r join fetch r.session where r.id = :id")
    Optional<AgentRun> findByIdWithSession(@Param("id") String id);

    Optional<AgentRun> findFirstByUserIdOrderByCreatedAtDesc(Long userId);

    List<AgentRun> findByStatusIn(
            List<com.gahyeonbot.services.ai.agent.AgentRunStatus> statuses);

    List<AgentRun> findByStatusAndUpdatedAtBefore(
            com.gahyeonbot.services.ai.agent.AgentRunStatus status,
            LocalDateTime cutoff);
}
