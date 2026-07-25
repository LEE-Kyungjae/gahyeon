package com.gahyeonbot.services.ai;

import com.gahyeonbot.services.weather.City;
import com.gahyeonbot.services.weather.WeatherService;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.Arrays;
import java.util.Locale;
import java.util.stream.Collectors;

/**
 * 가현이 에이전트가 선택적으로 호출하는 정형 날씨 도구.
 *
 * 자연어 의도나 날짜 표현을 여기서 추측하지 않습니다. 모델이 대화 문맥을
 * 해석해 canonical 인자를 만들고, 이 클래스는 계약 검증과 조회만 담당합니다.
 */
@Component
@RequiredArgsConstructor
public class WeatherTools {

    private static final ZoneId SERVICE_ZONE = ZoneId.of("Asia/Seoul");

    private final WeatherService weatherService;

    @Tool(
            name = "get_current_weather",
            description = """
                    지원 도시의 현재 날씨를 조회한다.
                    사용자가 현재 기온, 비, 바람, 지금 날씨를 물을 때 사용한다.
                    city_code는 get_supported_weather_locations 결과의 code를 사용한다.
                    """
    )
    public String getCurrentWeather(
            @ToolParam(description = "조회할 도시의 canonical code (예: SEOUL, COLMAR, PRAGUE)")
            String cityCode
    ) {
        return weatherService.buildCurrentWeatherMessage(requireCity(cityCode));
    }

    @Tool(
            name = "get_weather_forecast",
            description = """
                    지원 도시의 날짜 범위별 일기예보를 조회한다.
                    상대 날짜 표현은 현재 날짜를 기준으로 계산한 ISO-8601 날짜로 전달한다.
                    최대 16일 예보만 제공되며 city_code는 get_supported_weather_locations 결과의 code를 사용한다.
                    """
    )
    public String getForecast(
            @ToolParam(description = "조회할 도시의 canonical code (예: SEOUL, COLMAR, PRAGUE)")
            String cityCode,
            @ToolParam(description = "조회 시작일, ISO-8601 yyyy-MM-dd")
            String startDate,
            @ToolParam(description = "조회 종료일, ISO-8601 yyyy-MM-dd")
            String endDate
    ) {
        LocalDate start = requireDate(startDate, "start_date");
        LocalDate end = requireDate(endDate, "end_date");
        if (end.isBefore(start)) {
            throw new IllegalArgumentException("end_date는 start_date보다 빠를 수 없어.");
        }
        LocalDate today = LocalDate.now(SERVICE_ZONE);
        if (start.isBefore(today)) {
            throw new IllegalArgumentException("과거 날짜의 예보는 조회할 수 없어.");
        }
        if (end.isAfter(today.plusDays(15))) {
            throw new IllegalArgumentException("예보는 오늘부터 최대 16일까지만 조회할 수 있어.");
        }
        return weatherService.buildForecastMessage(requireCity(cityCode), start, end);
    }

    @Tool(
            name = "get_supported_weather_locations",
            description = """
                    날씨 도구가 지원하는 도시의 canonical code, 한국어 이름, 국가 목록을 반환한다.
                    사용자 위치를 city_code로 확정할 수 없을 때 호출한다.
                    """
    )
    public String getSupportedLocations() {
        return Arrays.stream(City.values())
                .map(city -> "%s | %s | %s".formatted(city.name(), city.getKoreanName(), city.getCountry()))
                .collect(Collectors.joining("\n"));
    }

    private City requireCity(String cityCode) {
        if (cityCode == null || cityCode.isBlank()) {
            throw new IllegalArgumentException("city_code가 필요해.");
        }
        try {
            return City.valueOf(cityCode.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException(
                    "지원하지 않는 city_code야. get_supported_weather_locations를 먼저 호출해.", e);
        }
    }

    private LocalDate requireDate(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + "가 필요해.");
        }
        try {
            return LocalDate.parse(value.trim());
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException(fieldName + "는 yyyy-MM-dd 형식이어야 해.", e);
        }
    }
}
