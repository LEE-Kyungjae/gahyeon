package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.entity.NewsletterTheme;
import com.gahyeonbot.services.notification.DmSubscriptionService;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.OptionMapping;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class DmOptOut extends AbstractCommand {

    private final DmSubscriptionService dmSubscriptionService;

    @Override
    public String getName() {
        return Description.DM_OPTOUT_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.DM_OPTOUT_NAME_KO);
    }

    @Override
    public String getDescription() {
        return Description.DM_OPTOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.DM_OPTOUT_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        OptionData theme = new OptionData(OptionType.STRING, "theme", "해제할 뉴스레터 테마 (미지정 시 GitHub 트렌딩)", false);
        for (NewsletterTheme t : NewsletterTheme.values()) {
            theme.addChoice(t.getDisplayName(), t.getCode());
        }
        return List.of(theme);
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        NewsletterTheme theme = NewsletterTheme.fromCode(
                event.getOption("theme", NewsletterTheme.GITHUB_TRENDING.getCode(), OptionMapping::getAsString));
        dmSubscriptionService.optOut(event.getUser().getIdLong(), theme);
        event.reply("[%s] 구독을 껐습니다. 이후 해당 테마 발송 대상에서 제외됩니다.".formatted(theme.getDisplayName()))
                .setEphemeral(true)
                .queue();
    }
}
