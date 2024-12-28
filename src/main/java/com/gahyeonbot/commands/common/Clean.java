package com.gahyeonbot.commands.common;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.service.MessageCleanService;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionMapping;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;

public class Clean extends AbstractCommand {
    private final MessageCleanService messageCleanService;

    public Clean(MessageCleanService messageCleanService) {
        this.messageCleanService = messageCleanService;
    }

    @Override
    public String getName() {
        return Description.CLEAN_NAME;
    }

    @Override
    public String getDescription() {
        return Description.CLEAN_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.CLEAN_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of(
                new OptionData(OptionType.INTEGER, "line", "최근순으로 채팅을 삭제합니다. (최대 1000줄)", false)
                        .setMinValue(1)
                        .setMaxValue(1000),
                new OptionData(OptionType.INTEGER, "my", "최근 1000개의 채팅에서 최신순으로 지정한 값의 내 채팅을 삭제합니다.", false)
                        .setMinValue(1)
                        .setMaxValue(1000)
        );
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());
        event.deferReply().queue(); // 응답 시간 연장을 요청
        var channel = event.getChannel();
        OptionMapping lineOption = event.getOption("line");
        OptionMapping myOption = event.getOption("my");

        if (myOption != null && lineOption != null) {
            ResponseUtil.replyError(event, "한 번에 하나의 옵션만 선택할 수 있습니다.");
            return;
        }

        if (myOption != null) {
            int linesToDelete = myOption.getAsInt();
            messageCleanService.deleteUserMessages(channel, event, linesToDelete);
        } else if (lineOption != null) {
            int linesToDelete = lineOption.getAsInt();
            messageCleanService.deleteMessages(channel, event, linesToDelete);
        } else {
            ResponseUtil.replyError(event, "삭제할 줄 수를 입력해주세요.");
        }
    }
}
