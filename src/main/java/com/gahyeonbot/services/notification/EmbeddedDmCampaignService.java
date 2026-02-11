package com.gahyeonbot.services.notification;

import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.services.ai.ConversationHistoryService;
import com.gahyeonbot.services.ai.GlmService;
import com.gahyeonbot.services.weather.WeatherService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
public class EmbeddedDmCampaignService {

    private static final DateTimeFormatter RUN_DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;

    private final DmSubscriptionService dmSubscriptionService;
    private final DmDispatchService dmDispatchService;
    private final ConversationHistoryService conversationHistoryService;
    private final WeatherService weatherService;
    private final GlmService glmService;

    @Value("${notifications.dm.embedded-enabled:true}")
    private boolean embeddedEnabled;

    @Value("${notifications.dm.schedule-zone:Asia/Seoul}")
    private String scheduleZone;

    @Scheduled(
            cron = "${notifications.dm.embedded-cron:0 0 10 * * *}",
            zone = "${notifications.dm.schedule-zone:Asia/Seoul}"
    )
    public void runDailyDmCampaign() {
        if (!embeddedEnabled) {
            return;
        }
        if (!glmService.isEnabled()) {
            log.warn("내장 DM 캠페인 스킵: GLM API 키가 설정되지 않았습니다.");
            return;
        }

        List<DmSubscription> subscribers = dmSubscriptionService.getOptedInSubscriptions();
        if (subscribers.isEmpty()) {
            log.info("내장 DM 캠페인 대상자가 없습니다.");
            return;
        }

        String runId = buildRunId();
        String weatherContext = safeWeatherContext();
        int sent = 0;
        int failed = 0;

        for (DmSubscription subscription : subscribers) {
            Long userId = subscription.getUserId();
            String conversationContext = safeConversationContext(userId);
            String generatedMessage = glmService.generatePeriodicDmMessage(userId, conversationContext, weatherContext);
            String dedupeKey = runId + "-" + userId;

            DmDispatchService.DispatchResult result =
                    dmDispatchService.dispatchGeneratedMessage(runId, userId, generatedMessage, dedupeKey);

            if (result.isSent()) {
                sent++;
            } else {
                failed++;
            }
        }

        log.info("내장 DM 캠페인 완료 - runId: {}, 대상: {}, 성공: {}, 실패/스킵: {}",
                runId, subscribers.size(), sent, failed);
    }

    private String buildRunId() {
        LocalDate today = LocalDate.now(ZoneId.of(scheduleZone));
        return "embedded-" + today.format(RUN_DATE_FORMAT);
    }

    private String safeConversationContext(Long userId) {
        try {
            return conversationHistoryService.buildContext(userId);
        } catch (Exception e) {
            log.warn("대화 컨텍스트 조회 실패 - userId: {}, reason: {}", userId, e.getMessage());
            return "";
        }
    }

    private String safeWeatherContext() {
        try {
            return weatherService.getWeatherContext();
        } catch (Exception e) {
            log.warn("날씨 컨텍스트 조회 실패: {}", e.getMessage());
            return "";
        }
    }
}
