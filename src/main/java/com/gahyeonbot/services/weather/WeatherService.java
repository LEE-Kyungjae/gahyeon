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
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * 날씨 데이터 서비스.
 * Open-Meteo API를 사용하여 여러 도시의 날씨를 조회하고 캐시합니다.
 *
 * @author GahyeonBot Team
 * @version 2.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherService {

    private static final int CACHE_DURATION_MINUTES = 30;

    private final WeatherRepository weatherRepository;
    private RestTemplate restTemplate;

    // 메모리 캐시 (도시별)
    private final Map<City, WeatherData> weatherCache = new ConcurrentHashMap<>();
    private LocalDateTime cacheTime;

    @PostConstruct
    public void initialize() {
        this.restTemplate = new RestTemplate();
        log.info("날씨 서비스 초기화 완료 - 대상 도시: {}개", City.values().length);
        // 시작 시 모든 도시 날씨 로드
        fetchAllCitiesWeather();
    }

    /**
     * 모든 도시의 현재 날씨 정보를 가져옵니다.
     *
     * @return 도시별 날씨 데이터 맵
     */
    public Map<City, WeatherData> getAllCitiesWeather() {
        // 캐시 확인
        if (!weatherCache.isEmpty() && cacheTime != null &&
                cacheTime.plusMinutes(CACHE_DURATION_MINUTES).isAfter(LocalDateTime.now())) {
            return new HashMap<>(weatherCache);
        }

        // DB에서 최신 데이터 조회
        List<WeatherData> latestData = weatherRepository.findLatestForAllCities();
        Map<City, WeatherData> result = new HashMap<>();

        for (WeatherData weather : latestData) {
            try {
                City city = City.valueOf(weather.getCity());
                result.put(city, weather);
                weatherCache.put(city, weather);
            } catch (IllegalArgumentException e) {
                log.warn("알 수 없는 도시 코드: {}", weather.getCity());
            }
        }

        if (!result.isEmpty()) {
            this.cacheTime = LocalDateTime.now();
        }

        return result;
    }

    /**
     * 대화에 사용할 날씨 컨텍스트 문자열 생성
     * 국가별로 그룹화하여 보기 좋게 정리
     *
     * @return 날씨 정보 문자열
     */
    public String getWeatherContext() {
        Map<City, WeatherData> allWeather = getAllCitiesWeather();

        if (allWeather.isEmpty()) {
            return "";
        }

        // 국가별로 그룹화
        Map<String, List<Map.Entry<City, WeatherData>>> byCountry = allWeather.entrySet().stream()
                .collect(Collectors.groupingBy(e -> e.getKey().getCountry()));

        StringBuilder sb = new StringBuilder("[현재 날씨 정보]\n");

        // 한국을 먼저, 나머지는 알파벳 순
        List<String> countries = new ArrayList<>(byCountry.keySet());
        countries.sort((a, b) -> {
            if (a.equals("한국")) return -1;
            if (b.equals("한국")) return 1;
            return a.compareTo(b);
        });

        for (String country : countries) {
            sb.append("▸ ").append(country).append(": ");
            List<String> cityWeathers = byCountry.get(country).stream()
                    .map(e -> {
                        WeatherData w = e.getValue();
                        return String.format("%s %.1f°C %s",
                                w.getCityName(), w.getTemperature(), w.getWeatherDescription());
                    })
                    .collect(Collectors.toList());
            sb.append(String.join(" / ", cityWeathers)).append("\n");
        }

        return sb.toString().trim();
    }

    /**
     * 매시간 날씨 데이터 업데이트 (정각마다)
     */
    @Scheduled(cron = "0 0 * * * *")
    @Transactional
    public void scheduledWeatherUpdate() {
        log.info("스케줄된 날씨 업데이트 시작 - {}개 도시", City.values().length);
        fetchAllCitiesWeather();
    }

    /**
     * 모든 도시의 날씨 데이터를 가져와 저장합니다.
     */
    @Transactional
    public void fetchAllCitiesWeather() {
        int successCount = 0;
        int failCount = 0;

        for (City city : City.values()) {
            try {
                WeatherData weather = fetchWeatherForCity(city);
                if (weather != null) {
                    weatherRepository.save(weather);
                    weatherCache.put(city, weather);
                    successCount++;
                } else {
                    failCount++;
                }
                // API 과부하 방지
                Thread.sleep(100);
            } catch (Exception e) {
                log.error("도시 날씨 조회 실패 - {}: {}", city.getKoreanName(), e.getMessage());
                failCount++;
            }
        }

        this.cacheTime = LocalDateTime.now();
        log.info("날씨 업데이트 완료 - 성공: {}, 실패: {}", successCount, failCount);
    }

    /**
     * 특정 도시의 날씨 데이터를 API에서 가져옵니다.
     */
    private WeatherData fetchWeatherForCity(City city) {
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    city.buildApiUrl(),
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<>() {}
            );

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return parseWeatherResponse(city, response.getBody());
            }
        } catch (Exception e) {
            log.error("API 호출 실패 - {}: {}", city.getKoreanName(), e.getMessage());
        }
        return null;
    }

    /**
     * API 응답을 파싱하여 WeatherData 객체 생성
     */
    @SuppressWarnings("unchecked")
    private WeatherData parseWeatherResponse(City city, Map<String, Object> response) {
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
                .city(city.name())
                .cityName(city.getKoreanName())
                .country(city.getCountry())
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
