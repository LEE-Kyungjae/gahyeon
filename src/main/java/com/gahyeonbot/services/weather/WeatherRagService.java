package com.gahyeonbot.services.weather;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.entity.WeatherData;
import com.gahyeonbot.entity.WeatherForecast;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * pgvector를 사용한 날씨 RAG 인덱싱/검색 서비스.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherRagService {

    private static final String SOURCE_TYPE_CURRENT = "current";
    private static final String SOURCE_TYPE_FORECAST = "forecast";

    private final JdbcTemplate jdbcTemplate;
    private final AppCredentialsConfig appCredentialsConfig;
    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${weather.rag.enabled:true}")
    private boolean ragEnabled;

    @Value("${weather.rag.embedding-model:text-embedding-3-small}")
    private String embeddingModel;

    @Value("${weather.rag.top-k:4}")
    private int topK;

    @Value("${weather.rag.min-similarity:0.35}")
    private double minSimilarity;

    private volatile Boolean pgVectorReady;

    @Transactional
    public void indexCurrentWeather(WeatherData weatherData) {
        if (weatherData == null || !isUsable()) {
            return;
        }

        String chunkText = buildCurrentChunk(weatherData);
        List<List<Double>> embeddings = embedTexts(List.of(chunkText));
        if (embeddings.isEmpty()) {
            return;
        }

        upsertChunk(
                weatherData.getCity(),
                weatherData.getCityName(),
                weatherData.getCountry(),
                SOURCE_TYPE_CURRENT,
                weatherData.getFetchedAt().toLocalDate(),
                weatherData.getFetchedAt(),
                chunkText,
                embeddings.get(0)
        );
    }

    @Transactional
    public void indexForecasts(List<WeatherForecast> forecasts) {
        if (forecasts == null || forecasts.isEmpty() || !isUsable()) {
            return;
        }

        List<String> chunkTexts = new ArrayList<>(forecasts.size());
        for (WeatherForecast forecast : forecasts) {
            chunkTexts.add(buildForecastChunk(forecast));
        }

        List<List<Double>> embeddings = embedTexts(chunkTexts);
        if (embeddings.size() != forecasts.size()) {
            log.warn("예보 임베딩 수 불일치 - 기대: {}, 실제: {}", forecasts.size(), embeddings.size());
            return;
        }

        for (int i = 0; i < forecasts.size(); i++) {
            WeatherForecast forecast = forecasts.get(i);
            upsertChunk(
                    forecast.getCity(),
                    forecast.getCityName(),
                    forecast.getCountry(),
                    SOURCE_TYPE_FORECAST,
                    forecast.getForecastDate(),
                    forecast.getFetchedAt(),
                    chunkTexts.get(i),
                    embeddings.get(i)
            );
        }
    }

    @Transactional(readOnly = true)
    public String searchWeatherContext(String userQuestion) {
        if (userQuestion == null || userQuestion.isBlank() || !isUsable()) {
            return "";
        }

        Optional<City> mentionedCity = extractMentionedCity(userQuestion);
        List<List<Double>> queryEmbedding = embedTexts(List.of(userQuestion));
        if (queryEmbedding.isEmpty()) {
            return "";
        }

        String vectorLiteral = toVectorLiteral(queryEmbedding.get(0));

        List<RetrievedChunk> chunks = mentionedCity
                .map(city -> searchByCity(vectorLiteral, city.name()))
                .orElseGet(() -> searchWithoutCity(vectorLiteral));

        if (chunks.isEmpty()) {
            return "";
        }

        StringBuilder context = new StringBuilder("[RAG 날씨 검색 결과]\n");
        for (RetrievedChunk chunk : chunks) {
            context.append("- ")
                    .append(chunk.cityName)
                    .append("(")
                    .append(chunk.country)
                    .append(") ")
                    .append(chunk.sourceType.equals(SOURCE_TYPE_CURRENT) ? "현재" : "예보")
                    .append(" [유사도 ")
                    .append(String.format("%.2f", chunk.similarity))
                    .append("]: ")
                    .append(chunk.chunkText)
                    .append("\n");
        }
        return context.toString().trim();
    }

    private List<RetrievedChunk> searchByCity(String vectorLiteral, String cityCode) {
        return jdbcTemplate.query(
                """
                SELECT city_name, country, source_type, source_date, fetched_at, chunk_text, similarity
                FROM (
                    SELECT city_name, country, source_type, source_date, fetched_at, chunk_text,
                           (1 - (embedding <=> CAST(? AS vector))) AS similarity
                    FROM weather_rag_chunks
                    WHERE city = ?
                ) ranked
                WHERE similarity >= ?
                ORDER BY similarity DESC, fetched_at DESC
                LIMIT ?
                """,
                this::mapChunk,
                vectorLiteral,
                cityCode,
                minSimilarity,
                topK
        );
    }

    private List<RetrievedChunk> searchWithoutCity(String vectorLiteral) {
        return jdbcTemplate.query(
                """
                SELECT city_name, country, source_type, source_date, fetched_at, chunk_text, similarity
                FROM (
                    SELECT city_name, country, source_type, source_date, fetched_at, chunk_text,
                           (1 - (embedding <=> CAST(? AS vector))) AS similarity
                    FROM weather_rag_chunks
                ) ranked
                WHERE similarity >= ?
                ORDER BY similarity DESC, fetched_at DESC
                LIMIT ?
                """,
                this::mapChunk,
                vectorLiteral,
                minSimilarity,
                topK
        );
    }

    private RetrievedChunk mapChunk(java.sql.ResultSet rs, int rowNum) throws java.sql.SQLException {
        return new RetrievedChunk(
                rs.getString("city_name"),
                rs.getString("country"),
                rs.getString("source_type"),
                rs.getDate("source_date").toLocalDate(),
                rs.getTimestamp("fetched_at").toLocalDateTime(),
                rs.getString("chunk_text"),
                rs.getDouble("similarity")
        );
    }

    @Transactional
    public void cleanupOldChunks(LocalDate cutoffDate) {
        if (cutoffDate == null || !isUsable()) {
            return;
        }

        jdbcTemplate.update("DELETE FROM weather_rag_chunks WHERE source_date < ?", cutoffDate);
    }

    private boolean isUsable() {
        if (!ragEnabled) {
            return false;
        }

        String apiKey = appCredentialsConfig.getOpenaiApiKey();
        if (apiKey == null || apiKey.isBlank() || apiKey.startsWith("your_")) {
            return false;
        }

        return isPgVectorReady();
    }

    private boolean isPgVectorReady() {
        if (pgVectorReady != null) {
            return pgVectorReady;
        }

        try {
            Integer count = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'",
                    Integer.class
            );
            pgVectorReady = count != null && count > 0;
        } catch (Exception e) {
            log.info("pgvector 비활성 또는 PostgreSQL 아님 - Weather RAG 비활성화");
            pgVectorReady = false;
        }

        return pgVectorReady;
    }

    private List<List<Double>> embedTexts(List<String> texts) {
        if (texts.isEmpty()) {
            return Collections.emptyList();
        }

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(appCredentialsConfig.getOpenaiApiKey());

            Map<String, Object> body = Map.of(
                    "model", embeddingModel,
                    "input", texts
            );

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    "https://api.openai.com/v1/embeddings",
                    HttpMethod.POST,
                    request,
                    new ParameterizedTypeReference<>() {}
            );

            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                return Collections.emptyList();
            }

            Object dataObj = response.getBody().get("data");
            if (!(dataObj instanceof List<?> dataList)) {
                return Collections.emptyList();
            }

            List<List<Double>> vectors = new ArrayList<>(dataList.size());
            for (Object item : dataList) {
                if (!(item instanceof Map<?, ?> itemMap)) {
                    continue;
                }
                Object embObj = itemMap.get("embedding");
                if (!(embObj instanceof List<?> embList)) {
                    continue;
                }

                List<Double> vector = new ArrayList<>(embList.size());
                for (Object value : embList) {
                    if (value instanceof Number number) {
                        vector.add(number.doubleValue());
                    }
                }
                vectors.add(vector);
            }

            return vectors;
        } catch (Exception e) {
            log.warn("날씨 RAG 임베딩 생성 실패: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private void upsertChunk(
            String city,
            String cityName,
            String country,
            String sourceType,
            LocalDate sourceDate,
            LocalDateTime fetchedAt,
            String chunkText,
            List<Double> embedding
    ) {
        String vectorLiteral = toVectorLiteral(embedding);

        jdbcTemplate.update(
                "DELETE FROM weather_rag_chunks WHERE city = ? AND source_type = ? AND source_date = ?",
                city,
                sourceType,
                sourceDate
        );

        jdbcTemplate.update(
                """
                INSERT INTO weather_rag_chunks
                (city, city_name, country, source_type, source_date, fetched_at, chunk_text, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, CAST(? AS vector))
                """,
                city,
                cityName,
                country,
                sourceType,
                sourceDate,
                fetchedAt,
                chunkText,
                vectorLiteral
        );
    }

    private String buildCurrentChunk(WeatherData weatherData) {
        return String.format(
                "%s(%s) 현재 날씨: %.1f도, %s, 강수량 %.1fmm, 강수확률 %d%%, 풍속 %.1fkm/h, 관측시각 %s",
                weatherData.getCityName(),
                weatherData.getCountry(),
                weatherData.getTemperature(),
                weatherData.getWeatherDescription(),
                weatherData.getPrecipitation(),
                weatherData.getPrecipitationProbability() != null ? weatherData.getPrecipitationProbability() : 0,
                weatherData.getWindSpeed(),
                weatherData.getFetchedAt()
        );
    }

    private String buildForecastChunk(WeatherForecast forecast) {
        return String.format(
                "%s(%s) %s 예보: %s, 최저 %.1f도, 최고 %.1f도, 강수확률 %d%%, 예보수집시각 %s",
                forecast.getCityName(),
                forecast.getCountry(),
                forecast.getForecastDate(),
                forecast.getWeatherDescription(),
                forecast.getTempMin(),
                forecast.getTempMax(),
                forecast.getPrecipitationProbability() != null ? forecast.getPrecipitationProbability() : 0,
                forecast.getFetchedAt()
        );
    }

    private String toVectorLiteral(List<Double> embedding) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < embedding.size(); i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append(embedding.get(i));
        }
        sb.append(']');
        return sb.toString();
    }

    private Optional<City> extractMentionedCity(String question) {
        String normalized = normalize(question);
        for (City city : City.values()) {
            String korean = normalize(city.getKoreanName());
            String english = normalize(city.name());
            if (normalized.contains(korean) || normalized.contains(english)) {
                return Optional.of(city);
            }
        }
        return Optional.empty();
    }

    private String normalize(String value) {
        return value.toLowerCase()
                .replaceAll("[\\s_\\-]", "");
    }

    private record RetrievedChunk(
            String cityName,
            String country,
            String sourceType,
            LocalDate sourceDate,
            LocalDateTime fetchedAt,
            String chunkText,
            double similarity
    ) {
    }
}
