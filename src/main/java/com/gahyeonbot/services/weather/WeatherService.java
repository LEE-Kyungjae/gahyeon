package com.gahyeonbot.services.weather;

import com.gahyeonbot.entity.WeatherData;
import com.gahyeonbot.repository.WeatherRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 날씨 데이터 서비스.
 * Open-Meteo API를 사용하여 서울 날씨를 조회하고 캐시합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherService {

    private static final String WEATHER_API_URL =
            "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780" +
            "&current=temperature_2m,precipitation,wind_speed_10m,weather_code" +
            "&hourly=precipitation_probability&timezone=Asia/Seoul";

    private static final int CACHE_DURATION_MINUTES = 30;

    private final WeatherRepository weatherRepository;
    private RestTemplate restTemplate;

    // 메모리 캐시 (DB 조회 최소화)
    private WeatherData cachedWeather;
    private LocalDateTime cacheTime;

    @PostConstruct
    public void initialize() {
        this.restTemplate = new RestTemplate();
        log.info("날씨 서비스 초기화 완료");
        // 시작 시 날씨 데이터 로드
        fetchAndSaveWeather();
    }

    /**
     * 현재 날씨 정보를 가져옵니다.
     * 캐시된 데이터가 있으면 반환하고, 없으면 DB에서 조회합니다.
     *
     * @return 날씨 데이터 (없으면 빈 Optional)
     */
    public Optional<WeatherData> getCurrentWeather() {
        // 메모리 캐시 확인
        if (cachedWeather != null && cacheTime != null &&
                cacheTime.plusMinutes(CACHE_DURATION_MINUTES).isAfter(LocalDateTime.now())) {
            return Optional.of(cachedWeather);
        }

        // DB에서 최신 데이터 조회
        Optional<WeatherData> latest = weatherRepository.findLatest();
        latest.ifPresent(weather -> {
            this.cachedWeather = weather;
            this.cacheTime = LocalDateTime.now();
        });

        return latest;
    }

    /**
     * 대화에 사용할 날씨 컨텍스트 문자열 생성
     *
     * @return 날씨 정보 문자열
     */
    public String getWeatherContext() {
        return getCurrentWeather()
                .map(weather -> String.format(
                        "[현재 서울 날씨] 기온: %.1f°C, %s, 풍속: %.1fkm/h, 강수확률: %d%%",
                        weather.getTemperature(),
                        weather.getWeatherDescription(),
                        weather.getWindSpeed(),
                        weather.getPrecipitationProbability() != null ? weather.getPrecipitationProbability() : 0
                ))
                .orElse("");
    }

    /**
     * 매시간 날씨 데이터 업데이트 (정각마다)
     */
    @Scheduled(cron = "0 0 * * * *")
    @Transactional
    public void scheduledWeatherUpdate() {
        log.info("스케줄된 날씨 업데이트 시작");
        fetchAndSaveWeather();
    }

    /**
     * API에서 날씨 데이터를 가져와 저장합니다.
     */
    @Transactional
    public void fetchAndSaveWeather() {
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    WEATHER_API_URL,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<>() {}
            );

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                WeatherData weather = parseWeatherResponse(response.getBody());
                weatherRepository.save(weather);

                // 메모리 캐시 업데이트
                this.cachedWeather = weather;
                this.cacheTime = LocalDateTime.now();

                log.info("날씨 데이터 업데이트 완료 - 기온: {}°C, {}",
                        weather.getTemperature(), weather.getWeatherDescription());
            }
        } catch (Exception e) {
            log.error("날씨 데이터 조회 실패", e);
        }
    }

    /**
     * API 응답을 파싱하여 WeatherData 객체 생성
     */
    @SuppressWarnings("unchecked")
    private WeatherData parseWeatherResponse(Map<String, Object> response) {
        Map<String, Object> current = (Map<String, Object>) response.get("current");
        Map<String, Object> hourly = (Map<String, Object>) response.get("hourly");

        Double temperature = ((Number) current.get("temperature_2m")).doubleValue();
        Double precipitation = ((Number) current.get("precipitation")).doubleValue();
        Double windSpeed = ((Number) current.get("wind_speed_10m")).doubleValue();
        Integer weatherCode = ((Number) current.get("weather_code")).intValue();

        // 현재 시간대의 강수 확률
        Integer precipitationProbability = 0;
        if (hourly != null && hourly.get("precipitation_probability") != null) {
            List<Integer> probabilities = (List<Integer>) hourly.get("precipitation_probability");
            if (!probabilities.isEmpty()) {
                precipitationProbability = probabilities.get(0);
            }
        }

        return WeatherData.builder()
                .temperature(temperature)
                .precipitation(precipitation)
                .windSpeed(windSpeed)
                .precipitationProbability(precipitationProbability)
                .weatherDescription(getWeatherDescription(weatherCode))
                .fetchedAt(LocalDateTime.now())
                .build();
    }

    /**
     * WMO 날씨 코드를 한글 설명으로 변환
     * https://open-meteo.com/en/docs 참고
     */
    private String getWeatherDescription(int code) {
        return switch (code) {
            case 0 -> "맑음";
            case 1, 2, 3 -> "구름 조금";
            case 45, 48 -> "안개";
            case 51, 53, 55 -> "이슬비";
            case 56, 57 -> "얼어붙는 이슬비";
            case 61, 63, 65 -> "비";
            case 66, 67 -> "얼어붙는 비";
            case 71, 73, 75 -> "눈";
            case 77 -> "싸락눈";
            case 80, 81, 82 -> "소나기";
            case 85, 86 -> "눈 소나기";
            case 95 -> "뇌우";
            case 96, 99 -> "우박 동반 뇌우";
            default -> "흐림";
        };
    }
}
