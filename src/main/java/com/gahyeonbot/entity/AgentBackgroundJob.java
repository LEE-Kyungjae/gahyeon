package com.gahyeonbot.entity;

import com.gahyeonbot.services.ai.agent.AgentBackgroundJobStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "agent_background_jobs")
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentBackgroundJob {
    @Id
    @Column(length = 36)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "run_id", nullable = false)
    private AgentRun run;

    @Column(name = "job_type", nullable = false, length = 100)
    private String jobType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String payload;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AgentBackgroundJobStatus status;

    @Column(name = "available_at", nullable = false)
    private LocalDateTime availableAt;

    @Column(nullable = false)
    private int attempts;

    @Column(name = "max_attempts", nullable = false)
    private int maxAttempts;

    @Column(name = "locked_at")
    private LocalDateTime lockedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "last_error", columnDefinition = "TEXT")
    private String lastError;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
