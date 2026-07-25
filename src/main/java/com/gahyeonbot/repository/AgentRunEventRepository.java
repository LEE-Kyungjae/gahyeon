package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentRunEvent;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AgentRunEventRepository extends JpaRepository<AgentRunEvent, Long> {
    List<AgentRunEvent> findByRunIdOrderBySequenceAsc(String runId);
}
