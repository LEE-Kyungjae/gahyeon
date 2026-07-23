package com.gahyeonbot.services.notification;

import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.NewsletterTheme;
import com.gahyeonbot.repository.DmSubscriptionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DmSubscriptionService {
    private static final String DEFAULT_TIMEZONE = "Asia/Seoul";
    private static final NewsletterTheme DEFAULT_THEME = NewsletterTheme.GITHUB_TRENDING;

    private final DmSubscriptionRepository subscriptionRepository;

    private DmSubscription loadOrNew(Long userId, NewsletterTheme theme) {
        return subscriptionRepository.findByUserIdAndTheme(userId, theme)
                .orElseGet(() -> DmSubscription.builder()
                        .userId(userId)
                        .theme(theme)
                        .timezone(DEFAULT_TIMEZONE)
                        .build());
    }

    @Transactional
    public DmSubscription optIn(Long userId, NewsletterTheme theme) {
        DmSubscription subscription = loadOrNew(userId, theme);
        subscription.setEnabled(true);
        subscription.setTimezone(DEFAULT_TIMEZONE);
        subscription.setOptedInAt(LocalDateTime.now());
        subscription.setOptedOutAt(null);
        return subscriptionRepository.save(subscription);
    }

    @Transactional
    public DmSubscription optOut(Long userId, NewsletterTheme theme) {
        DmSubscription subscription = loadOrNew(userId, theme);
        subscription.setEnabled(false);
        subscription.setTimezone(DEFAULT_TIMEZONE);
        subscription.setOptedOutAt(LocalDateTime.now());
        return subscriptionRepository.save(subscription);
    }

    @Transactional(readOnly = true)
    public DmSubscription getOrDefault(Long userId, NewsletterTheme theme) {
        return subscriptionRepository.findByUserIdAndTheme(userId, theme)
                .orElseGet(() -> DmSubscription.builder()
                        .userId(userId)
                        .theme(theme)
                        .enabled(false)
                        .timezone(DEFAULT_TIMEZONE)
                        .build());
    }

    @Transactional(readOnly = true)
    public boolean isOptedIn(Long userId, NewsletterTheme theme) {
        return subscriptionRepository.findByUserIdAndTheme(userId, theme)
                .map(subscription -> Boolean.TRUE.equals(subscription.getEnabled()))
                .orElse(false);
    }

    /** 특정 테마의 활성 구독자. */
    @Transactional(readOnly = true)
    public List<DmSubscription> getOptedInSubscriptions(NewsletterTheme theme) {
        return subscriptionRepository.findByThemeAndEnabledTrue(theme);
    }

    /** 한 사용자의 모든 테마 구독. */
    @Transactional(readOnly = true)
    public List<DmSubscription> getUserSubscriptions(Long userId) {
        return subscriptionRepository.findByUserId(userId);
    }

    // --- 하위호환: 테마 미지정 = 기본 테마(GitHub 트렌딩) ---

    @Transactional
    public DmSubscription optIn(Long userId) {
        return optIn(userId, DEFAULT_THEME);
    }

    @Transactional
    public DmSubscription optOut(Long userId) {
        return optOut(userId, DEFAULT_THEME);
    }

    @Transactional(readOnly = true)
    public DmSubscription getOrDefault(Long userId) {
        return getOrDefault(userId, DEFAULT_THEME);
    }

    @Transactional(readOnly = true)
    public boolean isOptedIn(Long userId) {
        return isOptedIn(userId, DEFAULT_THEME);
    }

    @Transactional(readOnly = true)
    public List<DmSubscription> getOptedInSubscriptions() {
        return getOptedInSubscriptions(DEFAULT_THEME);
    }
}
