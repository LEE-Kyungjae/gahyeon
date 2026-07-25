package com.gahyeonbot.entity;

import com.gahyeonbot.services.ai.agent.AgentEventType;
import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "agent_run_events",
        uniqueConstraints = @UniqueConstraint(name = "uq_agent_run_event_sequence",
                columnNames = {"run_id", "sequence"}))
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentRunEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "run_id", nullable = false)
    private AgentRun run;

    @Column(nullable = false)
    private long sequence;

    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false, length = 40)
    private AgentEventType eventType;

    @Column(nullable = false)
    private int step;

    @Column(name = "tool_name", length = 120)
    private String toolName;

    @Column(columnDefinition = "TEXT")
    private String payload;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
