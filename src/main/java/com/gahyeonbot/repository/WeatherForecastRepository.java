package com.gahyeonbot.repository;

import com.gahyeonbot.entity.WeatherForecast;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

/**
 * 날씨 예보 Repository.
 * 예보 히스토리를 저장하고 날짜 거리에 따라 적절한 예보를 반환합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Repository
public interface WeatherForecastRepository extends JpaRepository<WeatherForecast, Long> {

    /**
     * 특정 도시, 특정 날짜의 가장 최신 예보 조회
     * (가까운 날짜용 - 최신 예보가 정확함)
     */
    @Query("SELECT f FROM WeatherForecast f " +
            "WHERE f.city = :city AND f.forecastDate = :date " +
            "ORDER BY f.fetchedAt DESC LIMIT 1")
    Optional<WeatherForecast> findLatestForecast(
            @Param("city") String city,
            @Param("date") LocalDate date);

    /**
     * 특정 도시, 특정 날짜의 가장 첫번째 예보 조회
     * (먼 날짜용 - 최초 예보 보존)
     */
    @Query("SELECT f FROM WeatherForecast f " +
            "WHERE f.city = :city AND f.forecastDate = :date " +
            "ORDER BY f.fetchedAt ASC LIMIT 1")
    Optional<WeatherForecast> findFirstForecast(
            @Param("city") String city,
            @Param("date") LocalDate date);

    /**
     * 특정 도시의 7일간 최신 예보 조회 (날짜별 최신 1건씩)
     */
    @Query(value = """
            SELECT DISTINCT ON (forecast_date) *
            FROM weather_forecast
            WHERE city = :city
              AND forecast_date BETWEEN :startDate AND :endDate
            ORDER BY forecast_date, fetched_at DESC
            """, nativeQuery = true)
    List<WeatherForecast> findLatestForecastsForWeek(
            @Param("city") String city,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);

    /**
     * 모든 도시의 특정 날짜 최신 예보 조회 (도시별 최신 1건씩)
     */
    @Query(value = """
            SELECT DISTINCT ON (city) *
            FROM weather_forecast
            WHERE forecast_date = :date
            ORDER BY city, fetched_at DESC
            """, nativeQuery = true)
    List<WeatherForecast> findLatestForecastsForDate(@Param("date") LocalDate date);

    /**
     * 오래된 예보 히스토리 정리 (30일 이상 지난 예보 대상 날짜)
     */
    @Modifying
    @Query("DELETE FROM WeatherForecast f WHERE f.forecastDate < :cutoffDate")
    void deleteOldForecasts(@Param("cutoffDate") LocalDate cutoffDate);

    /**
     * 중복 체크: 같은 도시, 같은 예보 날짜, 같은 조회 시간대(시간 단위)에 이미 저장된 예보가 있는지
     */
    @Query("SELECT COUNT(f) > 0 FROM WeatherForecast f " +
            "WHERE f.city = :city AND f.forecastDate = :forecastDate " +
            "AND FUNCTION('DATE_TRUNC', 'hour', f.fetchedAt) = FUNCTION('DATE_TRUNC', 'hour', :fetchedAt)")
    boolean existsSameHourForecast(
            @Param("city") String city,
            @Param("forecastDate") LocalDate forecastDate,
            @Param("fetchedAt") java.time.LocalDateTime fetchedAt);
}
