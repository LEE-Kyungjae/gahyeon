package com.gahyeonbot.services.notification;

import com.gahyeonbot.entity.DmSubscription;
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

    private final DmSubscriptionRepository subscriptionRepository;

    @Transactional
    public DmSubscription optIn(Long userId) {
        DmSubscription subscription = subscriptionRepository.findById(userId)
                .orElseGet(() -> DmSubscription.builder()
                        .userId(userId)
                        .timezone(DEFAULT_TIMEZONE)
                        .build());

        subscription.setEnabled(true);
        subscription.setTimezone(DEFAULT_TIMEZONE);
        subscription.setOptedInAt(LocalDateTime.now());
        subscription.setOptedOutAt(null);
        return subscriptionRepository.save(subscription);
    }

    @Transactional
    public DmSubscription optOut(Long userId) {
        DmSubscription subscription = subscriptionRepository.findById(userId)
                .orElseGet(() -> DmSubscription.builder()
                        .userId(userId)
                        .timezone(DEFAULT_TIMEZONE)
                        .build());

        subscription.setEnabled(false);
        subscription.setTimezone(DEFAULT_TIMEZONE);
        subscription.setOptedOutAt(LocalDateTime.now());
        return subscriptionRepository.save(subscription);
    }

    @Transactional(readOnly = true)
    public DmSubscription getOrDefault(Long userId) {
        return subscriptionRepository.findById(userId)
                .orElseGet(() -> DmSubscription.builder()
                        .userId(userId)
                        .enabled(false)
                        .timezone(DEFAULT_TIMEZONE)
                        .build());
    }

    @Transactional(readOnly = true)
    public boolean isOptedIn(Long userId) {
        return subscriptionRepository.findById(userId)
                .map(subscription -> Boolean.TRUE.equals(subscription.getEnabled()))
                .orElse(false);
    }

    @Transactional(readOnly = true)
    public List<DmSubscription> getOptedInSubscriptions() {
        return subscriptionRepository.findByEnabledTrue();
    }
}
