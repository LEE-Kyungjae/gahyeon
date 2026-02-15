package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.services.weather.City;
import com.gahyeonbot.services.weather.WeatherRagService;
import com.gahyeonbot.services.weather.WeatherService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.TemporalAdjusters;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class Weather extends AbstractCommand {

    private final WeatherService weatherService;
    private final WeatherRagService weatherRagService;

    @Override
    public String getName() {
        return Description.WEATHER_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.WEATHER_NAME_KO);
    }

    @Override
    public String getDescription() {
        return Description.WEATHER_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.WEATHER_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        // Discord slash commands require declared options to accept user input.
        // Keep it minimal: optional free-form query (e.g., "콜마르 다음주").
        return List.of(
                new OptionData(OptionType.STRING, "query", "도시/날짜를 자연어로 입력 (예: 콜마르 다음주, 서울 내일)", false)
        );
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        log.info("명령어 실행 시작: {}", getName());

        try {
            event.deferReply().complete();
        } catch (Exception e) {
            log.error("deferReply 실패 - 다른 인스턴스가 처리 중이거나 타임아웃: {}", e.getMessage());
            return;
        }

        try {
            String query = event.getOption("query") != null ? event.getOption("query").getAsString() : null;
            String message;

            if (query == null || query.isBlank()) {
                // 기본: 서울 포함 전체 컨텍스트(현재 + 7일 예보 + 여행지 요약)
                message = weatherService.getWeatherContext();
            } else {
                message = buildWeatherMessageFromQuery(query);
            }

            // Embed description limit is generous, but keep it safe for Discord clients.
            if (message.length() > 3800) {
                message = message.substring(0, 3797) + "...";
            }

            event.getHook().editOriginalEmbeds(EmbedUtil.createNormalEmbed(message).build()).complete();
        } catch (Exception e) {
            log.error("날씨 명령어 실행 중 오류", e);
            try {
                event.getHook().editOriginal("날씨 정보를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.").complete();
            } catch (Exception ignored) {
            }
        }
    }

    private boolean looksLikeWeatherQuery(String text) {
        String s = text == null ? "" : text.toLowerCase();
        return s.contains("날씨")
                || s.contains("예보")
                || s.contains("기온")
                || s.contains("온도")
                || s.contains("강수")
                || s.contains("weather")
                || s.contains("forecast")
                || s.contains("temperature");
    }

    private String buildWeatherMessageFromQuery(String query) {
        String q = query.trim();
        String normalized = q.toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-]", "");

        var cityOpt = weatherRagService.tryExtractMentionedCity(q);
        City city = cityOpt.orElse(City.SEOUL);

        // If the user explicitly wrote "<place> 날씨" and <place> isn't supported, show a helpful message.
        String locationHint = extractLocationHint(q);
        if (looksLikeWeatherQuery(q)
                && cityOpt.isEmpty()
                && locationHint != null
                && !isTimeWordOnly(locationHint)) {
            return buildUnsupportedCityMessage(locationHint);
        }

        DateRange range = parseDateRange(normalized);
        boolean wantsCurrent = normalized.contains("지금")
                || normalized.contains("현재")
                || normalized.contains("now");

        boolean wantsForecast = normalized.contains("예보")
                || normalized.contains("forecast")
                || range != null;

        if (wantsForecast) {
            LocalDate start = range != null ? range.start : LocalDate.now();
            LocalDate end = range != null ? range.end : LocalDate.now().plusDays(6);
            String msg = weatherService.buildForecastMessage(city, start, end);
            if (msg.contains("찾지 못했어")) {
                // Fallback to RAG if DB doesn't have enough yet.
                String rag = weatherRagService.searchWeatherMessage(q);
                return rag.isBlank() ? msg : rag;
            }
            return msg;
        }

        if (wantsCurrent) {
            return weatherService.buildCurrentWeatherMessage(city);
        }

        // Default: show current + 7-day for the resolved city.
        return weatherService.buildCurrentWeatherMessage(city)
                + "\n\n"
                + weatherService.buildForecastMessage(city, LocalDate.now(), LocalDate.now().plusDays(6));
    }

    private String extractLocationHint(String query) {
        String q = query.trim();
        String lower = q.toLowerCase(Locale.ROOT);

        int idx = lower.indexOf("날씨");
        if (idx <= 0) {
            idx = lower.indexOf("weather");
        }
        if (idx <= 0) {
            return null;
        }

        String candidate = q.substring(0, idx).trim();
        candidate = candidate.replaceAll("[\"'`]", "").trim();
        if (candidate.isBlank()) {
            return null;
        }

        // If it's a long phrase, use the last token (e.g., "다음주 아이슬란드" -> "아이슬란드").
        String[] parts = candidate.split("\\s+");
        String last = parts[parts.length - 1].trim();
        if (last.isBlank()) {
            return null;
        }
        // Strip common particles.
        last = last.replaceAll("(의|에서|에|로|으로)$", "");
        return last.isBlank() ? null : last;
    }

    private boolean isTimeWordOnly(String s) {
        String n = s.toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-]", "");
        return n.contains("오늘")
                || n.contains("내일")
                || n.contains("모레")
                || n.contains("이번주")
                || n.contains("다음주")
                || n.contains("주말")
                || n.contains("thisweek")
                || n.contains("nextweek")
                || n.contains("weekend");
    }

    private record DateRange(LocalDate start, LocalDate end) {}

    private DateRange parseDateRange(String normalizedLowerNoSpaces) {
        LocalDate today = LocalDate.now();
        if (normalizedLowerNoSpaces.contains("오늘") || normalizedLowerNoSpaces.contains("today")) {
            return new DateRange(today, today);
        }
        if (normalizedLowerNoSpaces.contains("내일") || normalizedLowerNoSpaces.contains("tomorrow")) {
            LocalDate d = today.plusDays(1);
            return new DateRange(d, d);
        }
        if (normalizedLowerNoSpaces.contains("모레")) {
            LocalDate d = today.plusDays(2);
            return new DateRange(d, d);
        }
        if (normalizedLowerNoSpaces.contains("주말") || normalizedLowerNoSpaces.contains("weekend")) {
            LocalDate sat = today.with(TemporalAdjusters.nextOrSame(DayOfWeek.SATURDAY));
            LocalDate sun = sat.with(TemporalAdjusters.nextOrSame(DayOfWeek.SUNDAY));
            return new DateRange(sat, sun);
        }
        if (normalizedLowerNoSpaces.contains("다음주") || normalizedLowerNoSpaces.contains("nextweek")) {
            LocalDate start = today.with(TemporalAdjusters.next(DayOfWeek.MONDAY));
            return new DateRange(start, start.plusDays(6));
        }
        if (normalizedLowerNoSpaces.contains("이번주") || normalizedLowerNoSpaces.contains("thisweek") || normalizedLowerNoSpaces.contains("주간")) {
            LocalDate start = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
            return new DateRange(start, start.plusDays(6));
        }

        DayOfWeek weekday = extractWeekday(normalizedLowerNoSpaces);
        if (weekday != null) {
            LocalDate d;
            if (normalizedLowerNoSpaces.contains("다음주") || normalizedLowerNoSpaces.contains("nextweek")) {
                LocalDate weekStart = today.with(TemporalAdjusters.next(DayOfWeek.MONDAY));
                d = weekStart.with(TemporalAdjusters.nextOrSame(weekday));
            } else if (normalizedLowerNoSpaces.contains("이번주") || normalizedLowerNoSpaces.contains("thisweek")) {
                LocalDate weekStart = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
                d = weekStart.with(TemporalAdjusters.nextOrSame(weekday));
            } else {
                d = today.with(TemporalAdjusters.nextOrSame(weekday));
            }
            return new DateRange(d, d);
        }

        return null;
    }

    private DayOfWeek extractWeekday(String normalizedLowerNoSpaces) {
        if (normalizedLowerNoSpaces.contains("월요일") || normalizedLowerNoSpaces.contains("월욜") || normalizedLowerNoSpaces.contains("monday")) return DayOfWeek.MONDAY;
        if (normalizedLowerNoSpaces.contains("화요일") || normalizedLowerNoSpaces.contains("화욜") || normalizedLowerNoSpaces.contains("tuesday")) return DayOfWeek.TUESDAY;
        if (normalizedLowerNoSpaces.contains("수요일") || normalizedLowerNoSpaces.contains("수욜") || normalizedLowerNoSpaces.contains("wednesday")) return DayOfWeek.WEDNESDAY;
        if (normalizedLowerNoSpaces.contains("목요일") || normalizedLowerNoSpaces.contains("목욜") || normalizedLowerNoSpaces.contains("thursday")) return DayOfWeek.THURSDAY;
        if (normalizedLowerNoSpaces.contains("금요일") || normalizedLowerNoSpaces.contains("금욜") || normalizedLowerNoSpaces.contains("friday")) return DayOfWeek.FRIDAY;
        if (normalizedLowerNoSpaces.contains("토요일") || normalizedLowerNoSpaces.contains("토욜") || normalizedLowerNoSpaces.contains("saturday")) return DayOfWeek.SATURDAY;
        if (normalizedLowerNoSpaces.contains("일요일") || normalizedLowerNoSpaces.contains("일욜") || normalizedLowerNoSpaces.contains("sunday")) return DayOfWeek.SUNDAY;
        return null;
    }

    private String buildUnsupportedCityMessage(String query) {
        String supported = java.util.Arrays.stream(City.values())
                .map(c -> c.getKoreanName() + "(" + c.getCountry() + ")")
                .collect(Collectors.joining(", "));

        return """
                아직 지원하지 않는 도시야: %s

                현재 지원 도시: %s

                예) `/날씨`
                예) `/날씨 query:콜마르 다음주`
                """.formatted(query.trim(), supported).trim();
    }
}
