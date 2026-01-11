package com.gahyeonbot.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 날씨 예보 데이터 엔티티.
 * 7일간의 예보를 히스토리로 보관하여 예보 정확도 분석 가능.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Entity
@Table(name = "weather_forecast",
        indexes = {
                @Index(name = "idx_forecast_city_date", columnList = "city, forecast_date"),
                @Index(name = "idx_forecast_fetched", columnList = "fetched_at DESC")
        })
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WeatherForecast {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 도시 코드 (City enum name)
     */
    @Column(name = "city", nullable = false, length = 50)
    private String city;

    /**
     * 도시 한글 이름
     */
    @Column(name = "city_name", nullable = false, length = 50)
    private String cityName;

    /**
     * 국가 이름
     */
    @Column(name = "country", nullable = false, length = 50)
    private String country;

    /**
     * 예보 대상 날짜
     */
    @Column(name = "forecast_date", nullable = false)
    private LocalDate forecastDate;

    /**
     * 최고 기온 (섭씨)
     */
    @Column(name = "temp_max", nullable = false)
    private Double tempMax;

    /**
     * 최저 기온 (섭씨)
     */
    @Column(name = "temp_min", nullable = false)
    private Double tempMin;

    /**
     * 강수 확률 (%)
     */
    @Column(name = "precipitation_probability")
    private Integer precipitationProbability;

    /**
     * 날씨 설명 (맑음, 흐림, 비 등)
     */
    @Column(name = "weather_description", length = 50)
    private String weatherDescription;

    /**
     * 데이터 조회 시점 (예보를 가져온 시간)
     */
    @Column(name = "fetched_at", nullable = false)
    @Builder.Default
    private LocalDateTime fetchedAt = LocalDateTime.now();
}
