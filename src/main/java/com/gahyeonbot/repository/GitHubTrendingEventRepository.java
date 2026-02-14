package com.gahyeonbot.repository;

import com.gahyeonbot.entity.GitHubTrendingEvent;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface GitHubTrendingEventRepository extends JpaRepository<GitHubTrendingEvent, Long> {

    List<GitHubTrendingEvent> findBySnapshotDateAndSentAtIsNullOrderByCreatedAtAsc(LocalDate snapshotDate);
}

