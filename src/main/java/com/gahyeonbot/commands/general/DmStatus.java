package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.entity.DmSubscription;
import com.gahyeonbot.entity.NewsletterTheme;
import com.gahyeonbot.services.notification.DmSubscriptionService;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class DmStatus extends AbstractCommand {

    private final DmSubscriptionService dmSubscriptionService;

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
        long userId = event.getUser().getIdLong();

        Map<NewsletterTheme, Boolean> enabledByTheme = new EnumMap<>(NewsletterTheme.class);
        for (DmSubscription s : dmSubscriptionService.getUserSubscriptions(userId)) {
            enabledByTheme.put(s.getTheme(), Boolean.TRUE.equals(s.getEnabled()));
        }

        StringBuilder sb = new StringBuilder("**뉴스레터 구독 상태**\n");
        for (NewsletterTheme t : NewsletterTheme.values()) {
            boolean on = enabledByTheme.getOrDefault(t, false);
            sb.append("- %s: **%s**\n".formatted(t.getDisplayName(), on ? "ON" : "OFF"));
        }
        sb.append("\n`/dm수신 theme:<테마>` 로 켜고 `/dm거부 theme:<테마>` 로 끕니다.");

        event.reply(sb.toString()).setEphemeral(true).queue();
    }
}
