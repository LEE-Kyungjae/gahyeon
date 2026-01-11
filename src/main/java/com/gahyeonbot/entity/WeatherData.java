package com.gahyeonbot.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 날씨 데이터 엔티티.
 * Open-Meteo API에서 가져온 날씨 정보를 저장합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Entity
@Table(name = "weather_data")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WeatherData {

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
     * 현재 기온 (섭씨)
     */
    @Column(name = "temperature", nullable = false)
    private Double temperature;

    /**
     * 강수량 (mm)
     */
    @Column(name = "precipitation", nullable = false)
    private Double precipitation;

    /**
     * 풍속 (km/h)
     */
    @Column(name = "wind_speed", nullable = false)
    private Double windSpeed;

    /**
     * 강수 확률 (%) - 현재 시간대
     */
    @Column(name = "precipitation_probability")
    private Integer precipitationProbability;

    /**
     * 날씨 설명 (맑음, 흐림, 비 등)
     */
    @Column(name = "weather_description")
    private String weatherDescription;

    /**
     * 데이터 조회 시간
     */
    @Column(name = "fetched_at", nullable = false)
    @Builder.Default
    private LocalDateTime fetchedAt = LocalDateTime.now();
}
