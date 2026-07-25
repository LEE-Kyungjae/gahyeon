package com.gahyeonbot.entity;

import com.gahyeonbot.services.ai.agent.AgentApprovalStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "agent_approvals",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_agent_approval_call",
                columnNames = {"run_id", "tool_name", "argument_hash"}))
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentApproval {
    @Id
    @Column(length = 36)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "run_id", nullable = false)
    private AgentRun run;

    @Column(name = "tool_name", nullable = false, length = 120)
    private String toolName;

    @Column(name = "tool_arguments", nullable = false, columnDefinition = "TEXT")
    private String toolArguments;

    @Column(name = "argument_hash", nullable = false, length = 64)
    private String argumentHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AgentApprovalStatus status;

    @Column(name = "requested_at", nullable = false)
    private LocalDateTime requestedAt;

    @Column(name = "decided_at")
    private LocalDateTime decidedAt;

    @Column(name = "decided_by")
    private Long decidedBy;

    @Column(name = "consumed_at")
    private LocalDateTime consumedAt;
}
