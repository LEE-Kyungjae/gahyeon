package com.gahyeonbot.repository;

import com.gahyeonbot.entity.DmDeliveryLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface DmDeliveryLogRepository extends JpaRepository<DmDeliveryLog, Long> {
    boolean existsByDedupeKey(String dedupeKey);
}
