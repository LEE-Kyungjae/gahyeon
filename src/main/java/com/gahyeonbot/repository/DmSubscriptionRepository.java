package com.gahyeonbot.repository;

import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.DmSubscriptionId;
import com.gahyeonbot.entity.NewsletterTheme;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DmSubscriptionRepository extends JpaRepository<DmSubscription, DmSubscriptionId> {

    /** 특정 테마의 활성 구독자 (테마별 발송용). */
    List<DmSubscription> findByThemeAndEnabledTrue(NewsletterTheme theme);

    /** 한 사용자의 모든 테마 구독 (구독 상태 표시용). */
    List<DmSubscription> findByUserId(Long userId);

    Optional<DmSubscription> findByUserIdAndTheme(Long userId, NewsletterTheme theme);
}
