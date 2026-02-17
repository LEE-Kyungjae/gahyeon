package com.gahyeonbot.repository;

import com.gahyeonbot.entity.GitHubTrendingEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface GitHubTrendingEventRepository extends JpaRepository<GitHubTrendingEvent, Long> {

    List<GitHubTrendingEvent> findBySnapshotDateAndSentAtIsNullOrderByCreatedAtAsc(LocalDate snapshotDate);

    @Query("""
            select distinct e.snapshotDate
            from GitHubTrendingEvent e
            where e.sentAt is null
              and e.snapshotDate <= :today
            order by e.snapshotDate asc
            """)
    List<LocalDate> findDistinctPendingSnapshotDatesUpTo(@Param("today") LocalDate today);
}
