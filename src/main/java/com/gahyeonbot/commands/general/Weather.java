package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.services.weather.WeatherService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * 전체 날씨 현황을 빠르게 보는 legacy 명령어.
 *
 * 자연어 날씨 질문은 휴리스틱으로 해석하지 않고 /가현아 에이전트가
 * 정형 날씨 도구를 선택하도록 단일화합니다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class Weather extends AbstractCommand {

    private final WeatherService weatherService;

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
        return List.of();
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
            String message = weatherService.getWeatherContext();
            if (message == null || message.isBlank()) {
                message = "아직 날씨 데이터가 없어. 잠시 뒤 다시 봐줘.";
            }
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
}
