package com.gahyeonbot.services.notification;

import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.GitHubTrendingEvent;
import com.gahyeonbot.repository.GitHubTrendingEventRepository;
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
    private final GlmService glmService;

    @Value("${notifications.dm.trending-enabled:true}")
    private boolean trendingEnabled;

    @Value("${notifications.dm.schedule-zone:Asia/Seoul}")
    private String scheduleZone;

    @Scheduled(
            cron = "${notifications.dm.trending-cron:0 0 5 * * *}",
            zone = "${notifications.dm.schedule-zone:Asia/Seoul}"
    )
    public void runTrendingCampaign() {
        if (!trendingEnabled) {
            return;
        }

        LocalDate today = LocalDate.now(ZoneId.of(scheduleZone));
        LocalDate snapshotDate = today;
        List<GitHubTrendingEvent> events = trendingEventRepository
                .findBySnapshotDateAndSentAtIsNullOrderByCreatedAtAsc(snapshotDate);

        if (events.isEmpty()) {
            LocalDate yesterday = today.minusDays(1);
            snapshotDate = yesterday;
            events = trendingEventRepository.findBySnapshotDateAndSentAtIsNullOrderByCreatedAtAsc(snapshotDate);
        }

        if (events.isEmpty()) {
            // "신규만"이 목표라면 이벤트가 없으면 보내지 않는 게 맞음.
            // (기존처럼 스냅샷 전체를 보내고 싶다면 여기서 github_trending으로 fallback 하면 됨)
            log.info("GitHub 트렌딩 신규 이벤트 없음 - today: {}, yesterday: {}", today, today.minusDays(1));
            return;
        }

        List<GitHubTrending> repos = events.stream()
                .map(GitHubTrendingCampaignService::toTrendingEntityForDigest)
                .collect(Collectors.toList());

        String digest = glmService.generateTrendingDigest(repos);
        MessageEmbed embed = EmbedUtil.createGitHubTrendingEmbed(digest, repos).build();

        List<DmSubscription> subscribers = dmSubscriptionService.getOptedInSubscriptions();
        if (subscribers.isEmpty()) {
            log.info("GitHub 트렌딩 DM 대상자가 없습니다.");
            return;
        }

        String runId = "trending-" + snapshotDate.format(RUN_DATE_FORMAT);
        int sent = 0;
        int failed = 0;
        boolean shouldMarkEventsSent = false;

        for (DmSubscription subscription : subscribers) {
            Long userId = subscription.getUserId();
            // 동일한 snapshotDate 신규 이벤트 묶음은 사용자당 1회만 보내도록 dedupe.
            String dedupeKey = runId + "-" + userId;

            DmDispatchService.DispatchResult result =
                    dmDispatchService.dispatchEmbed(runId, userId, embed, dedupeKey);

            if (result.isSent()) {
                sent++;
                shouldMarkEventsSent = true;
            } else {
                failed++;
                if ("SKIPPED_DUPLICATE".equals(result.getStatus())) {
                    // 이미 같은 runId/userId로 발송(또는 처리)된 케이스면 이벤트도 "처리됨"으로 보는 게 자연스럽다.
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
        }

        log.info("GitHub 트렌딩 DM 캠페인 완료 - runId: {}, 레포: {}, 대상: {}, 성공: {}, 실패/스킵: {}",
                runId, repos.size(), subscribers.size(), sent, failed);
    }

    private static GitHubTrending toTrendingEntityForDigest(GitHubTrendingEvent e) {
        return GitHubTrending.builder()
                .snapshotDate(e.getSnapshotDate())
                .repoFullName(e.getRepoFullName())
                .repoUrl(e.getRepoUrl())
                .description(e.getDescription())
                .language(e.getLanguage())
                .starsTotal(e.getStarsTotal() != null ? e.getStarsTotal() : 0)
                .starsPeriod(e.getStarsPeriod())
                // Digest/Embed 생성을 위한 변환이라 persisted entity로 저장하지 않음.
                .createdAt(LocalDateTime.now())
                .build();
    }
}
