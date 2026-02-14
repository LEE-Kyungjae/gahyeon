package com.gahyeonbot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "github_trending", indexes = {
        @Index(name = "idx_github_trending_snapshot_date", columnList = "snapshot_date")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GitHubTrending {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "snapshot_date", nullable = false)
    private LocalDate snapshotDate;

    @Column(name = "repo_full_name", nullable = false, length = 255)
    private String repoFullName;

    @Column(name = "repo_url", nullable = false, length = 500)
    private String repoUrl;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "language", length = 100)
    private String language;

    @Column(name = "stars_total", nullable = false)
    @Builder.Default
    private Integer starsTotal = 0;

    @Column(name = "stars_period")
    private Integer starsPeriod;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
