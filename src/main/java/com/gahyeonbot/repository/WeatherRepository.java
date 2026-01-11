package com.gahyeonbot.repository;

import com.gahyeonbot.entity.WeatherData;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * 날씨 데이터 Repository.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Repository
public interface WeatherRepository extends JpaRepository<WeatherData, Long> {

    /**
     * 가장 최근 날씨 데이터 조회
     *
     * @return 최신 날씨 데이터
     */
    @Query("SELECT w FROM WeatherData w ORDER BY w.fetchedAt DESC LIMIT 1")
    Optional<WeatherData> findLatest();
}
