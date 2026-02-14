package com.gahyeonbot.services.notification;

import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.services.ai.GlmService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.entities.MessageEmbed;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class GitHubTrendingCampaignService {

    private static final DateTimeFormatter RUN_DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;

    private final DmSubscriptionService dmSubscriptionService;
    private final DmDispatchService dmDispatchService;
    private final GitHubTrendingRepository trendingRepository;
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
        List<GitHubTrending> repos = trendingRepository.findBySnapshotDateOrderByStarsPeriodDesc(today);

        if (repos.isEmpty()) {
            LocalDate yesterday = today.minusDays(1);
            repos = trendingRepository.findBySnapshotDateOrderByStarsPeriodDesc(yesterday);
            if (repos.isEmpty()) {
                log.info("GitHub 트렌딩 데이터 없음 - today: {}, yesterday: {}", today, yesterday);
                return;
            }
            log.info("GitHub 트렌딩: 어제({}) 데이터 사용", yesterday);
        }

        String digest = glmService.generateTrendingDigest(repos);
        MessageEmbed embed = EmbedUtil.createGitHubTrendingEmbed(digest, repos).build();

        List<DmSubscription> subscribers = dmSubscriptionService.getOptedInSubscriptions();
        if (subscribers.isEmpty()) {
            log.info("GitHub 트렌딩 DM 대상자가 없습니다.");
            return;
        }

        String runId = "trending-" + today.format(RUN_DATE_FORMAT);
        int sent = 0;
        int failed = 0;

        for (DmSubscription subscription : subscribers) {
            Long userId = subscription.getUserId();
            String dedupeKey = runId + "-" + userId;

            DmDispatchService.DispatchResult result =
                    dmDispatchService.dispatchEmbed(runId, userId, embed, dedupeKey);

            if (result.isSent()) {
                sent++;
            } else {
                failed++;
            }
        }

        log.info("GitHub 트렌딩 DM 캠페인 완료 - runId: {}, 레포: {}, 대상: {}, 성공: {}, 실패/스킵: {}",
                runId, repos.size(), subscribers.size(), sent, failed);
    }
}
