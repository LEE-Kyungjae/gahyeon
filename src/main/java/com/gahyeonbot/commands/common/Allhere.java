package com.gahyeonbot.commands.common;

import com.gahyeonbot.commands.ICommand;
import com.gahyeonbot.commands.Description;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.entities.channel.concrete.VoiceChannel;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class Allhere implements ICommand {
    @Override
    public String getName() {
        return Description.ALLHERE_NAME;
    }

    @Override
    public String getDescription() {
        return Description.ALLHERE_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.ALLHERE_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        // 이 명령어에는 추가 옵션이 필요하지 않으므로 빈 리스트 반환
        return new ArrayList<>();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        // 명령어 실행 사용자를 가져옴
        Member executor = event.getMember();
        if (executor.getVoiceState() == null || executor.getVoiceState().getChannel() == null) {
            event.reply("보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.").setEphemeral(true).queue();
            return;
        }
        if (executor == null) {
            event.reply("오류: 사용자 정보를 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }

        // 사용자가 현재 보이스 채널에 있는지 확인
        AudioChannel targetChannel = Objects.requireNonNull(executor.getVoiceState()).getChannel();
        if (targetChannel == null) {
            event.reply("보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.").setEphemeral(true).queue();
            return;
        }

        // 사용자가 VOICE_MOVE_OTHERS 권한을 가지고 있는지 확인
//        if (!executor.hasPermission(Permission.VOICE_MOVE_OTHERS)) {
//            event.reply("권한 부족: 다른 사용자를 이동시키기 위해 서버관리자에게 VOICE_MOVE_OTHERS 권한을 요창해주세요").setEphemeral(true).queue();
//            return;
//        }

        // 메시지 채널 가져오기
        MessageChannel messageChannel = event.getChannel();

        // 모든 보이스 채널 순회
        List<VoiceChannel> voiceChannels = event.getGuild().getVoiceChannels();
        for (VoiceChannel channel : voiceChannels) {
            if (channel.equals(targetChannel)) continue; // 사용자가 있는 채널은 건너뜀

            // 채널 내 모든 멤버 이동
            for (Member member : channel.getMembers()) {
                event.getGuild().moveVoiceMember(member, targetChannel).queue(
                        success -> messageChannel.sendMessage(member.getEffectiveName() + "님을 이동시켰습니다.").queue(),
                        error -> messageChannel.sendMessage("오류: " + member.getEffectiveName() + "님을 이동시킬 수 없습니다.").queue()
                );
            }
        }

        event.reply("모든 사용자를 현재 보이스 채널로 이동시켰습니다!").queue();
    }
}
