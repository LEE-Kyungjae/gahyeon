package com.gahyeonbot.commands;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.base.Description;
import net.dv8tion.jda.api.entities.Message;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionMapping;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class Clean implements ICommand {
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
        List<OptionData> data = new ArrayList<>();
        data.add(new OptionData(OptionType.INTEGER, "line", "최근순으로 채팅을 삭제합니다. (최대1000줄)", false)
                .setMinValue(1)
                .setMaxValue(1000));
        data.add(new OptionData(OptionType.INTEGER, "my", "최근 1000개의 채팅에서 최신순으로 지정한값의 내채팅을 삭제합니다", false)
                .setMinValue(1)
                .setMaxValue(1000));
        return data;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
//        if (!event.getGuild().getSelfMember().hasPermission(Permission.MESSAGE_MANAGE)) {
//            event.reply("봇에게 'MESSAGE_MANAGE' 권한이 없습니다. 관리자에게 요청해주세요.").setEphemeral(true).queue();
//            return;
//        }
//        if (!event.getMember().hasPermission(Permission.MESSAGE_MANAGE)) {
//            event.reply("이 명령어를 실행할 권한이 없습니다.").setEphemeral(true).queue();
//            return;
//        }
        MessageChannel channel = event.getChannel();
        OptionMapping lineOption = event.getOption("line");
        OptionMapping myOption = event.getOption("my");
        if (myOption != null && lineOption != null) {
            event.reply("한번에 옵션중 하나만 선택가능합니다.").setEphemeral(true).queue();
            return;
        }

        // "my" 옵션 처리
        if (myOption != null) {
            int line = myOption.getAsInt();
            deleteUserMessages(channel, event, line);
            return;
        }

        // "line" 옵션 처리
        if (lineOption != null) {
            // 권한 확인


            int line = lineOption.getAsInt();
            deleteMessages(channel, event, line);
        } else {
            event.reply("삭제할 줄수를 입력해주세요.").setEphemeral(true).queue();
        }
    }


    private void deleteUserMessages(MessageChannel channel, SlashCommandInteractionEvent event, int remaining) {
        if (remaining <= 0) {
            event.getHook().sendMessage("본인 채팅 삭제가 완료되었습니다.").setEphemeral(true).queue();
            return;
        }

        channel.getHistory().retrievePast(Math.min(remaining, 100)).queue(messages -> {
            // 본인의 메시지만 필터링
            List<Message> userMessages = messages.stream()
                    .filter(msg -> msg.getAuthor().equals(event.getUser()))
                    .limit(remaining)
                    .collect(Collectors.toList());

            if (userMessages.isEmpty()) {
                // 더 이상 삭제할 메시지가 없으면 종료
                event.getHook().sendMessage("더 이상 삭제할 본인 메시지가 없습니다.").setEphemeral(true).queue();
                return;
            }

            // 메시지 삭제
            channel.purgeMessages(userMessages);
            int deleted = userMessages.size();

            // 재귀 호출로 남은 메시지 삭제
            deleteUserMessages(channel, event, remaining - deleted);
        }, throwable -> {
            event.reply("채팅 삭제 중 오류가 발생했습니다.").setEphemeral(true).queue();
        });
    }


    private void deleteMessages(MessageChannel channel, SlashCommandInteractionEvent event, int remaining) {
        if (remaining <= 0) {
            event.getHook().sendMessage("채팅창을 청소했습니다.").setEphemeral(true).queue();
            return;
        }

        channel.getHistory().retrievePast(Math.min(remaining, 100)).queue(messages -> {
            if (messages.isEmpty()) {
                // 더 이상 삭제할 메시지가 없으면 종료
                event.getHook().sendMessage("더 이상 삭제할 메시지가 없습니다.").setEphemeral(true).queue();
                return;
            }

            // 메시지 삭제
            channel.purgeMessages(messages);
            int deleted = messages.size();

            // 재귀 호출로 남은 메시지 삭제
            deleteMessages(channel, event, remaining - deleted);
        }, throwable -> {
            event.reply("채팅 삭제 중 오류가 발생했습니다.").setEphemeral(true).queue();
        });
    }
}