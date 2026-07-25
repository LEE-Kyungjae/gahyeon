package com.gahyeonbot.services.weather;

import com.gahyeonbot.entity.WeatherForecast;
import com.gahyeonbot.repository.WeatherForecastRepository;
import com.gahyeonbot.repository.WeatherRepository;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class WeatherServiceForecastParsingTest {

    private final WeatherService service = new WeatherService(
            mock(WeatherRepository.class),
            mock(WeatherForecastRepository.class)
    );

    @Test
    void acceptsNullPrecipitationProbabilityFromOpenMeteo() {
        Map<String, Object> response = Map.of("daily", Map.of(
                "time", List.of("2026-07-25", "2026-07-26"),
                "temperature_2m_max", List.of(25.5, 26.0),
                "temperature_2m_min", List.of(18.0, 19.0),
                "weather_code", List.of(1, 61),
                "precipitation_probability_max", java.util.Arrays.asList(null, 70)
        ));

        List<WeatherForecast> forecasts = service.parseForecastResponse(City.PARIS, response);

        assertThat(forecasts).hasSize(2);
        assertThat(forecasts.get(0).getPrecipitationProbability()).isNull();
        assertThat(forecasts.get(1).getPrecipitationProbability()).isEqualTo(70);
    }

    @Test
    void skipsRowsMissingEssentialWeatherValues() {
        Map<String, Object> response = Map.of("daily", Map.of(
                "time", List.of("2026-07-25", "2026-07-26"),
                "temperature_2m_max", java.util.Arrays.asList(null, 26.0),
                "temperature_2m_min", List.of(18.0, 19.0),
                "weather_code", List.of(1, 61)
        ));

        List<WeatherForecast> forecasts = service.parseForecastResponse(City.PARIS, response);

        assertThat(forecasts).hasSize(1);
        assertThat(forecasts.getFirst().getForecastDate().toString()).isEqualTo("2026-07-26");
    }
}
