package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.services.notification.DmSubscriptionService;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class DmOptIn extends AbstractCommand {

    private final DmSubscriptionService dmSubscriptionService;

    @Override
    public String getName() {
        return Description.DM_OPTIN_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.DM_OPTIN_NAME_KO);
    }

    @Override
    public String getDescription() {
        return Description.DM_OPTIN_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.DM_OPTIN_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        dmSubscriptionService.optIn(event.getUser().getIdLong());
        event.reply("개인 메시지 수신을 활성화했습니다. 매일 오전 5시(KST) GitHub 트렌딩 다이제스트가 발송됩니다.")
                .setEphemeral(true)
                .queue();
    }
}
