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

import java.time.OffsetDateTime;

@Entity
@Table(name = "repo_readme_cache", indexes = {
        @Index(name = "idx_repo_readme_cache_repo", columnList = "repo_full_name"),
        @Index(name = "idx_repo_readme_cache_fetched_at", columnList = "readme_fetched_at"),
        @Index(name = "idx_repo_readme_cache_summary_updated_at", columnList = "summary_ko_updated_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RepoReadmeCache {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "repo_full_name", nullable = false, length = 255)
    private String repoFullName;

    @Column(name = "repo_url", nullable = false, length = 500)
    private String repoUrl;

    @Column(name = "readme_sha", nullable = false, length = 128)
    private String readmeSha;

    @Column(name = "readme_text", nullable = false, columnDefinition = "TEXT")
    private String readmeText;

    @Column(name = "readme_fetched_at", nullable = false)
    private OffsetDateTime readmeFetchedAt;

    @Column(name = "summary_ko", columnDefinition = "TEXT")
    private String summaryKo;

    @Column(name = "summary_ko_model", length = 100)
    private String summaryKoModel;

    @Column(name = "summary_ko_updated_at")
    private OffsetDateTime summaryKoUpdatedAt;
}

