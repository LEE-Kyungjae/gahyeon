package com.gahyeonbot.repository;

import com.gahyeonbot.entity.WeatherData;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
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
     * 특정 도시의 가장 최근 날씨 데이터 조회
     *
     * @param city 도시 코드
     * @return 최신 날씨 데이터
     */
    @Query("SELECT w FROM WeatherData w WHERE w.city = :city ORDER BY w.fetchedAt DESC LIMIT 1")
    Optional<WeatherData> findLatestByCity(@Param("city") String city);

    /**
     * 모든 도시의 최신 날씨 데이터 조회 (도시별 최신 1건씩)
     *
     * @return 각 도시별 최신 날씨 데이터 리스트
     */
    @Query(value = """
            SELECT DISTINCT ON (city) *
            FROM weather_data
            ORDER BY city, fetched_at DESC
            """, nativeQuery = true)
    List<WeatherData> findLatestForAllCities();
}
