package com.gahyeonbot.repository;

import com.gahyeonbot.entity.GitHubTrending;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface GitHubTrendingRepository extends JpaRepository<GitHubTrending, Long> {

    List<GitHubTrending> findBySnapshotDateOrderByStarsPeriodDesc(LocalDate snapshotDate);

    Optional<GitHubTrending> findTopByOrderBySnapshotDateDescIdDesc();

    Optional<GitHubTrending> findTopByRepoFullNameIgnoreCaseOrderBySnapshotDateDescIdDesc(String repoFullName);
}
