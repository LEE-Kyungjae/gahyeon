package com.gahyeonbot.repository;

import com.gahyeonbot.entity.DmSubscription;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DmSubscriptionRepository extends JpaRepository<DmSubscription, Long> {
    List<DmSubscription> findByEnabledTrue();
}
