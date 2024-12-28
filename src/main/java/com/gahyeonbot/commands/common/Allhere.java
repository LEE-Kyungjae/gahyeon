package com.gahyeonbot.commands.common;

import com.gahyeonbot.commands.util.*;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import net.dv8tion.jda.api.entities.channel.concrete.VoiceChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class Allhere extends AbstractCommand {

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
        return new ArrayList<>();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());
        Member executor = event.getMember();

        if (!isInVoiceChannel(executor)) {
            ResponseUtil.replyError(event, "보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.");
            return;
        }

        AudioChannel targetChannel = executor.getVoiceState().getChannel();
        List<String> movedMembers = new ArrayList<>();
        List<String> failedMembers = new ArrayList<>();

        // 사용자 이동 처리
        processMemberMovement(event, targetChannel, movedMembers, failedMembers);

        // 결과 메시지 처리
        sendMovementResult(event, movedMembers, failedMembers);
    }

    private boolean isInVoiceChannel(Member member) {
        return member != null && member.getVoiceState() != null && member.getVoiceState().getChannel() != null;
    }

    private void processMemberMovement(SlashCommandInteractionEvent event, AudioChannel targetChannel, List<String> movedMembers, List<String> failedMembers) {
        List<VoiceChannel> voiceChannels = event.getGuild().getVoiceChannels();

        for (VoiceChannel channel : voiceChannels) {
            if (channel.equals(targetChannel)) continue;

            for (Member member : channel.getMembers()) {
                event.getGuild().moveVoiceMember(member, targetChannel).queue(
                        success -> movedMembers.add(member.getEffectiveName()),
                        error -> failedMembers.add(member.getEffectiveName())
                );
            }
        }
    }

    private void sendMovementResult(SlashCommandInteractionEvent event, List<String> movedMembers, List<String> failedMembers) {
        StringBuilder resultMessage = new StringBuilder();

        if (!movedMembers.isEmpty()) {
            resultMessage.append("이동 완료: ").append(String.join(", ", movedMembers)).append("\n");
        }
        if (!failedMembers.isEmpty()) {
            resultMessage.append("이동 실패: ").append(String.join(", ", failedMembers)).append("\n");
        }

        if (resultMessage.length() > 0) {
            ResponseUtil.replyEmbed(event, EmbedUtil.nomal(resultMessage.toString()));
        } else {
            ResponseUtil.replyError(event, "다른 보이스 채널에 사용자가 없습니다.");
        }
    }
}
