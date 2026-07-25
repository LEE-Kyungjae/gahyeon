package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentRun;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface AgentRunRepository extends JpaRepository<AgentRun, String> {
    Optional<AgentRun> findByRequestId(String requestId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from AgentRun r where r.id = :id")
    Optional<AgentRun> findByIdForUpdate(@Param("id") String id);
}
