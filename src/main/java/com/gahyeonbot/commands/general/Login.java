package com.gahyeonbot.commands.general;

import com.gahyeonbot.adapters.discord.DiscordIdentityMapper;
import com.gahyeonbot.adapters.identity.ZezeStudioLinkService;
import com.gahyeonbot.commands.util.AbstractCommand;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.List;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

@Component
@RequiredArgsConstructor
public class Login extends AbstractCommand {
    private final DiscordIdentityMapper identities;
    private final ZezeStudioLinkService links;

    @Override public String getName() { return "login"; }
    @Override public Map<DiscordLocale, String> getNameLocalizations() { return localizeKorean("로그인"); }
    @Override public String getDescription() { return "Discord 계정을 ZezeStudio 공통 계정에 연결합니다."; }
    @Override public String getDetailedDescription() { return "/로그인 — 10분 동안 유효한 안전한 웹 로그인 링크를 발급합니다."; }
    @Override public List<OptionData> getOptions() { return List.of(); }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        try {
            var actor = identities.toActorId(event.getUser().getIdLong(), event.getUser().getName());
            var issued = links.issue(actor);
            event.reply("[ZezeStudio에서 로그인하고 계정 연결하기](" + issued.url() + ")\n"
                            + "이 링크는 10분 동안 한 번만 사용할 수 있습니다. 다른 사람에게 공유하지 마세요.\n"
                            + "만료: " + issued.expiresAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME) + " UTC")
                    .setEphemeral(true).queue();
        } catch (Exception error) {
            event.reply("현재 ZezeStudio 로그인을 시작할 수 없습니다. 잠시 후 다시 시도해 주세요.")
                    .setEphemeral(true).queue();
        }
    }
}
