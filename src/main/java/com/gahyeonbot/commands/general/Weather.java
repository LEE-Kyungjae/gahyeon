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

import java.util.List;
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
                // 지원하지 않는 도시를 물으면 엉뚱한 RAG 결과가 나올 수 있으니 먼저 안내
                if (looksLikeWeatherQuery(query) && weatherRagService.tryExtractMentionedCity(query).isEmpty()) {
                    message = buildUnsupportedCityMessage(query);
                } else {
                message = weatherRagService.searchWeatherMessage(query);
                if (message.isBlank()) {
                    message = "해당 질문으로는 날씨 정보를 찾지 못했어. 기본 날씨를 보여줄게.\n\n" + weatherService.getWeatherContext();
                }
                }
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
