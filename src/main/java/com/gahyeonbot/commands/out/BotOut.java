package com.gahyeonbot.commands.out;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.base.Description;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class BotOut implements ICommand {
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
        // 명령어 실행 사용자를 가져옴
        Member executor = event.getMember();
        if (executor == null || executor.getVoiceState() == null || executor.getVoiceState().getChannel() == null) {
            event.reply("보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.").setEphemeral(true).queue();
            return;
        }

        AudioChannel currentChannel = Objects.requireNonNull(executor.getVoiceState()).getChannel();

        // 사용자가 VOICE_MOVE_OTHERS 권한을 가지고 있는지 확인
//        if (!executor.hasPermission(Permission.VOICE_MOVE_OTHERS)) {
//            event.reply("권한 부족: 봇을 내보내기 위해 VOICE_MOVE_OTHERS 권한이 필요합니다.").setEphemeral(true).queue();
//            return;
//        }
//        if (!executor.hasPermission(Permission.ADMINISTRATOR) &&
//                !executor.hasPermission(Permission.VOICE_MOVE_OTHERS)) {
//            event.reply("권한 부족: VOICE_MOVE_OTHERS 권한이 필요합니다.")
//                    .setEphemeral(true).queue();
//            return;
//        }

        // 현재 보이스 채널의 모든 멤버 검사
        List<Member> botsToRemove = new ArrayList<>();
        for (Member member : currentChannel.getMembers()) {
            if (member.getUser().isBot()) {
                botsToRemove.add(member);
            }
        }

        // 봇 내보내기
        if (botsToRemove.isEmpty()) {
            event.reply("현재 채널에 봇이 없습니다.").setEphemeral(true).queue();
        } else {
            for (Member bot : botsToRemove) {
                event.getGuild().kickVoiceMember(bot).queue(
                        success -> event.getChannel().sendMessage(bot.getEffectiveName() + " 봇을 내보냈습니다.").queue(),
                        error -> event.getChannel().sendMessage("오류: " + bot.getEffectiveName() + " 봇을 내보낼 수 없습니다.").queue()
                );
            }
            event.reply("모든 봇을 내보냈습니다!").queue();
        }
    }
}
