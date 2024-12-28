package com.gahyeonbot.commands.out;

import com.gahyeonbot.commands.util.*;
import com.gahyeonbot.service.BotManagerService;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;

public class BotOut extends AbstractCommand {

    private final BotManagerService botManagerService;

    public BotOut(BotManagerService botManagerService) {
        this.botManagerService = botManagerService;
    }

    @Override
    public String getName() {
        return Description.BOTOUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.BOTOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.BOTOUT_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return new ArrayList<>();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());

        Member executor = event.getMember();

        // 보이스 채널 접속 여부 확인
        if (executor == null || executor.getVoiceState() == null || executor.getVoiceState().getChannel() == null) {
            ResponseUtil.replyError(event, "보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.");
            return;
        }

        // 봇 제거 로직 실행
        List<Member> removedBots = botManagerService.removeBotsFromChannel(event, executor.getVoiceState().getChannel());

        if (removedBots.isEmpty()) {
            ResponseUtil.replyError(event, "현재 채널에 봇이 없습니다.");
        } else {
            var embed = EmbedUtil.createBotOutEmbed(removedBots);
            ResponseUtil.replyEmbed(event, embed);
        }
    }
}
