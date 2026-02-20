package com.gahyeonbot.services.notification;

import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.GitHubTrendingEvent;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingEventRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import com.gahyeonbot.services.ai.GlmService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.entities.MessageEmbed;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class GitHubTrendingCampaignService {

    private static final DateTimeFormatter RUN_DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;

    private final DmSubscriptionService dmSubscriptionService;
    private final DmDispatchService dmDispatchService;
    private final GitHubTrendingEventRepository trendingEventRepository;
    private final RepoReadmeCacheRepository repoReadmeCacheRepository;
    private final GlmService glmService;

    @Value("${notifications.dm.trending-enabled:true}")
    private boolean trendingEnabled;

    @Value("${notifications.dm.schedule-zone:Asia/Seoul}")
    private String scheduleZone;

    @Scheduled(
            cron = "${notifications.dm.trending-cron:0 0 7 * * *}",
            zone = "${notifications.dm.schedule-zone:Asia/Seoul}"
    )
    public void runTrendingCampaign() {
        if (!trendingEnabled) {
            return;
        }

        LocalDate today = LocalDate.now(ZoneId.of(scheduleZone));
        List<LocalDate> pendingSnapshotDates = trendingEventRepository.findDistinctPendingSnapshotDatesUpTo(today);
        if (pendingSnapshotDates.isEmpty()) {
            log.info("GitHub 트렌딩 미발송 이벤트 없음 - upTo: {}", today);
            return;
        }

        List<DmSubscription> subscribers = dmSubscriptionService.getOptedInSubscriptions();
        if (subscribers.isEmpty()) {
            log.info("GitHub 트렌딩 DM 대상자가 없습니다.");
            return;
        }

        int totalRepos = 0;
        int totalSent = 0;
        int totalFailed = 0;
        int markedSnapshots = 0;

        for (LocalDate snapshotDate : pendingSnapshotDates) {
            List<GitHubTrendingEvent> events = trendingEventRepository
                    .findBySnapshotDateAndSentAtIsNullOrderByCreatedAtAsc(snapshotDate);
            if (events.isEmpty()) {
                continue;
            }

            List<GitHubTrending> repos = events.stream()
                    .map(this::toTrendingEntityForDigest)
                    .collect(Collectors.toList());
            totalRepos += repos.size();

            String digest = String.format("오늘의 GitHub 트렌딩 다이제스트 (%s, %d개)", snapshotDate, repos.size());
            MessageEmbed embed = EmbedUtil.createGitHubTrendingEmbed(digest, repos).build();

            String runId = "trending-" + snapshotDate.format(RUN_DATE_FORMAT);
            int sent = 0;
            int failed = 0;
            boolean shouldMarkEventsSent = false;

            for (DmSubscription subscription : subscribers) {
                Long userId = subscription.getUserId();
                String dedupeKey = runId + "-" + userId;

                DmDispatchService.DispatchResult result =
                        dmDispatchService.dispatchEmbed(runId, userId, embed, dedupeKey);

                if (result.isSent()) {
                    sent++;
                    shouldMarkEventsSent = true;
                } else {
                    failed++;
                    if ("SKIPPED_DUPLICATE".equals(result.getStatus())) {
                        shouldMarkEventsSent = true;
                    }
                }
            }

            if (shouldMarkEventsSent) {
                OffsetDateTime markedAt = OffsetDateTime.now();
                for (GitHubTrendingEvent e : events) {
                    if (e.getSentAt() == null) {
                        e.setSentAt(markedAt);
                    }
                }
                trendingEventRepository.saveAll(events);
                markedSnapshots++;
            }

            totalSent += sent;
            totalFailed += failed;
            log.info("GitHub 트렌딩 DM 스냅샷 처리 - runId: {}, 레포: {}, 대상: {}, 성공: {}, 실패/스킵: {}",
                    runId, repos.size(), subscribers.size(), sent, failed);
        }

        log.info("GitHub 트렌딩 DM 캠페인 완료 - snapshots: {}, marked: {}, 대상: {}, 레포: {}, 성공: {}, 실패/스킵: {}",
                pendingSnapshotDates.size(), markedSnapshots, subscribers.size(), totalRepos, totalSent, totalFailed);
    }

    private GitHubTrending toTrendingEntityForDigest(GitHubTrendingEvent e) {
        String descriptionForDigest = resolveDescriptionForDigest(e);

        return GitHubTrending.builder()
                .snapshotDate(e.getSnapshotDate())
                .repoFullName(e.getRepoFullName())
                .repoUrl(e.getRepoUrl())
                .description(descriptionForDigest)
                .language(e.getLanguage())
                .starsTotal(e.getStarsTotal() != null ? e.getStarsTotal() : 0)
                .starsPeriod(e.getStarsPeriod())
                // Digest/Embed 생성을 위한 변환이라 persisted entity로 저장하지 않음.
                .createdAt(LocalDateTime.now())
                .build();
    }

    private String resolveDescriptionForDigest(GitHubTrendingEvent event) {
        String repoFullName = event.getRepoFullName();
        if (repoFullName == null || repoFullName.isBlank()) {
            return event.getDescription();
        }

        try {
            RepoReadmeCache latest = repoReadmeCacheRepository.findTopByRepoFullNameOrderByReadmeFetchedAtDescIdDesc(repoFullName)
                    .orElse(null);
            if (latest == null) {
                return event.getDescription();
            }

            String latestSummary = normalized(latest.getSummaryKo());
            if (latestSummary != null) {
                return latestSummary;
            }

            String readmeText = latest.getReadmeText();
            if (readmeText == null || readmeText.isBlank()) {
                return findCachedSummaryOrDefault(repoFullName, event.getDescription());
            }

            String generated = glmService.summarizeRepoReadmeKo(repoFullName, readmeText);
            if (generated == null || generated.isBlank()) {
                return findCachedSummaryOrDefault(repoFullName, event.getDescription());
            }

            latest.setSummaryKo(generated.trim());
            latest.setSummaryKoModel(glmService.getActiveModel());
            latest.setSummaryKoUpdatedAt(OffsetDateTime.now());
            repoReadmeCacheRepository.save(latest);
            return latest.getSummaryKo();
        } catch (Exception ex) {
            log.warn("README summary resolve 실패 - repo: {}, reason: {}", repoFullName, ex.getMessage());
            return event.getDescription();
        }
    }

    private String findCachedSummaryOrDefault(String repoFullName, String fallback) {
        return repoReadmeCacheRepository
                .findTopByRepoFullNameAndSummaryKoIsNotNullOrderBySummaryKoUpdatedAtDescIdDesc(repoFullName)
                .map(RepoReadmeCache::getSummaryKo)
                .map(this::normalized)
                .orElse(fallback);
    }

    private String normalized(String text) {
        if (text == null) {
            return null;
        }
        String trimmed = text.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
