package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.*;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;

/**
 * 봇의 명령어 목록을 표시하는 명령어 클래스.
 * 사용자에게 봇이 지원하는 모든 명령어와 사용법을 안내합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
public class Info extends AbstractCommand {
    private final List<ICommand> commands;

    public Info(List<ICommand> commands) {
        this.commands = commands;
    }

    @Override
    public String getName() {
        return Description.INFO_NAME;
    }

    @Override
    public String getDescription() {
        return Description.INFO_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.INFO_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return new ArrayList<>();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        log.info("명령어 실행 시작: {}", getName());

        if (commands == null || commands.isEmpty()) {
            ResponseUtil.replyError(event, "현재 사용 가능한 명령어가 없습니다.");
            return;
        }

        var embed = EmbedUtil.createCommandListEmbed(commands, event);
        ResponseUtil.replyEmbed(event, embed);
    }
}
