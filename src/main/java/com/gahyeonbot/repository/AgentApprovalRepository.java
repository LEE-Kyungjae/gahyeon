package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentApproval;
import com.gahyeonbot.services.ai.agent.AgentApprovalStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AgentApprovalRepository extends JpaRepository<AgentApproval, String> {
    Optional<AgentApproval> findByRunIdAndToolNameAndArgumentHash(
            String runId, String toolName, String argumentHash);

    List<AgentApproval> findByRunIdOrderByRequestedAtAsc(String runId);

    Optional<AgentApproval> findFirstByRunIdAndStatusOrderByRequestedAtAsc(
            String runId, AgentApprovalStatus status);
}
