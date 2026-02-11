package com.gahyeonbot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "dm_delivery_log", indexes = {
        @Index(name = "idx_dm_delivery_log_run_id", columnList = "run_id"),
        @Index(name = "idx_dm_delivery_log_user_id", columnList = "user_id"),
        @Index(name = "idx_dm_delivery_log_attempted_at", columnList = "attempted_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DmDeliveryLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "run_id", nullable = false, length = 120)
    private String runId;

    @Column(name = "dedupe_key", nullable = false, unique = true, length = 200)
    private String dedupeKey;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "content_hash", nullable = false, length = 128)
    private String contentHash;

    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "attempted_at", nullable = false)
    private LocalDateTime attemptedAt;

    @PrePersist
    protected void onCreate() {
        attemptedAt = LocalDateTime.now();
    }
}
