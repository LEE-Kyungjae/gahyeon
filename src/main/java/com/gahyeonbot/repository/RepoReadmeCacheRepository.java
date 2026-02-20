package com.gahyeonbot.repository;

import com.gahyeonbot.entity.RepoReadmeCache;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface RepoReadmeCacheRepository extends JpaRepository<RepoReadmeCache, Long> {

    Optional<RepoReadmeCache> findTopByRepoFullNameOrderByReadmeFetchedAtDescIdDesc(String repoFullName);

    Optional<RepoReadmeCache> findTopByRepoFullNameAndSummaryKoIsNotNullOrderBySummaryKoUpdatedAtDescIdDesc(String repoFullName);
}
