package com.gahyeonbot.repository;

import com.gahyeonbot.entity.AgentSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AgentSessionRepository extends JpaRepository<AgentSession, String> {
    Optional<AgentSession> findBySessionKey(String sessionKey);
}
