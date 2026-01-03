package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.*;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.Permission;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import net.dv8tion.jda.api.entities.channel.concrete.VoiceChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 모든 보이스 채널의 사용자를 현재 보이스 채널로 이동시키는 명령어 클래스.
 * 서버의 모든 보이스 채널에 있는 사용자를 명령어 실행자의 보이스 채널로 집결시킵니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
@Component
public class Allhere extends AbstractCommand {

    @Override
    public String getName() {
        return Description.ALLHERE_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.ALLHERE_NAME_KO);
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
        log.info("명령어 실행 시작: {}", getName());

        if (event.getGuild() == null) {
            ResponseUtil.replyError(event, "서버에서만 사용할 수 있는 명령어입니다.");
            return;
        }

        if (!event.getGuild().getSelfMember().hasPermission(Permission.VOICE_MOVE_OTHERS)) {
            ResponseUtil.replyError(event, "봇에게 '사용자 이동' 권한이 필요합니다.");
            return;
        }

        Member executor = event.getMember();
        if (!isInVoiceChannel(executor)) {
            ResponseUtil.replyError(event, "보이스 채널에 접속 중이어야 명령어를 사용할 수 있습니다.");
            return;
        }

        AudioChannel targetChannel = executor.getVoiceState().getChannel();
        List<String> movedMembers = new ArrayList<>();
        List<String> failedMembers = new ArrayList<>();

        processMemberMovement(event, targetChannel, movedMembers, failedMembers);
    }

    private boolean isInVoiceChannel(Member member) {
        return member != null && member.getVoiceState() != null && member.getVoiceState().getChannel() != null;
    }

    private void processMemberMovement(
            SlashCommandInteractionEvent event,
            AudioChannel targetChannel,
            List<String> movedMembers,
            List<String> failedMembers
    ) {
        List<VoiceChannel> voiceChannels = event.getGuild().getVoiceChannels();
        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (VoiceChannel channel : voiceChannels) {
            if (channel.equals(targetChannel)) continue;

            for (Member member : channel.getMembers()) {
                CompletableFuture<Void> future = new CompletableFuture<>();
                event.getGuild().moveVoiceMember(member, targetChannel).queue(
                        success -> {
                            movedMembers.add(member.getEffectiveName());
                            future.complete(null);
                        },
                        error -> {
                            failedMembers.add(member.getEffectiveName());
                            future.complete(null);
                        }
                );
                futures.add(future);
            }
        }

        // 이동 대상이 아무도 없을 경우 즉시 메시지 반환
        if (futures.isEmpty()) {
            ResponseUtil.replyError(event, "다른 보이스 채널에 사용자가 없습니다.");
            return;
        }

        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenRun(() -> sendMovementResult(event, movedMembers, failedMembers));
    }

    private void sendMovementResult(
            SlashCommandInteractionEvent event,
            List<String> movedMembers,
            List<String> failedMembers
    ) {
        StringBuilder resultMessage = new StringBuilder();

        if (!movedMembers.isEmpty()) {
            resultMessage.append("✅ **이동 완료:** ").append(String.join(", ", movedMembers)).append("\n");
        }
        if (!failedMembers.isEmpty()) {
            resultMessage.append("❌ **이동 실패:** ").append(String.join(", ", failedMembers)).append("\n");
        }

        if (resultMessage.length() > 0) {
            ResponseUtil.replyEmbed(event, EmbedUtil.nomal(resultMessage.toString()));
        } else {
            ResponseUtil.replyError(event, "다른 보이스 채널에 사용자가 없습니다.");
        }
    }
}
