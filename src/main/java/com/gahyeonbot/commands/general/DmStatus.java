package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.services.notification.DmSubscriptionService;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class DmStatus extends AbstractCommand {

    private final DmSubscriptionService dmSubscriptionService;
    private static final DateTimeFormatter DATE_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Override
    public String getName() {
        return Description.DM_STATUS_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.DM_STATUS_NAME_KO);
    }

    @Override
    public String getDescription() {
        return Description.DM_STATUS_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.DM_STATUS_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        DmSubscription subscription = dmSubscriptionService.getOrDefault(event.getUser().getIdLong());

        String status = Boolean.TRUE.equals(subscription.getEnabled()) ? "ON" : "OFF";
        String optedInAt = subscription.getOptedInAt() == null
                ? "-"
                : subscription.getOptedInAt().format(DATE_TIME_FORMATTER);
        String optedOutAt = subscription.getOptedOutAt() == null
                ? "-"
                : subscription.getOptedOutAt().format(DATE_TIME_FORMATTER);

        String message = """
                DM 수신 상태: %s
                시간대: %s
                최근 수신 동의: %s
                최근 수신 거부: %s
                """.formatted(status, subscription.getTimezone(), optedInAt, optedOutAt);

        event.reply(message).setEphemeral(true).queue();
    }
}
