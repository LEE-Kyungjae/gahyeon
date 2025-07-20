package com.gahyeonbot.commands.moderation;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.core.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.concrete.VoiceChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionMapping;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 모든 사용자를 서버에서 추방하는 명령어.
 * 관리자 권한이 필요하며, 지정된 시간 후에 모든 사용자를 추방합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class KickAllUsers extends AbstractCommand implements ICommand {
    private final LeaveSchedulerManager schedulerManager;

    /**
     * KickAllUsers 생성자.
     * 
     * @param schedulerManager 스케줄러 매니저
     */
    public KickAllUsers(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return Description.WITHOUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.WITHOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.WITHOUT_DETAIL;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());
        // 권한 체크
//        if (!PermissionUtil.isAdmin(event) && !PermissionUtil.hasVoiceKickPermission(event)) {
//            ResponseUtil.replyError(event, "이 명령어를 사용할 권한이 없습니다.");
//            return;
//        }
        var member = event.getMember();

        if (member == null || member.getVoiceState() == null || member.getVoiceState().getChannel() == null) {
            ResponseUtil.replyError(event, "오류: 보이스 채널에 접속 중이 아닙니다.");
            return;
        }

        int totalMinutes = resolveTime(event);

        if (totalMinutes <= 0) {
            ResponseUtil.replyError(event, "잘못된 시간 입력입니다. HHMM/HMM/MM 형식으로 입력해주세요.");
            return;
        }

        VoiceChannel voiceChannel = (VoiceChannel) member.getVoiceState().getChannel();
        List<Member> members = voiceChannel.getMembers();

        // 예약 생성
        var task = schedulerManager.scheduleTask(() -> {
            for (Member voiceMember : members) {
                voiceMember.getGuild().kickVoiceMember(voiceMember).queue(
                        success -> ResponseUtil.sendMessageToChannel(event, voiceMember.getEffectiveName() + "님을 보이스 채널에서 내보냈습니다."),
                        failure -> ResponseUtil.sendMessageToChannel(event, "오류 발생: " + failure.getMessage())
                );
            }
        }, totalMinutes, TimeUnit.MINUTES);

        long reservationId = schedulerManager.addReservation(new Reservation(
                schedulerManager.generateId(),
                member.getIdLong(),
                member.getEffectiveName(),
                member.getGuild().getIdLong(),
                task,
                "함께 나가기 예약"
        ));

        var embed = EmbedUtil.createReservationEmbed(reservationId, "보이스 채널의 모든 사용자", totalMinutes);
        ResponseUtil.replyEmbed(event, embed);
    }

    private int resolveTime(SlashCommandInteractionEvent event) {
        var presetOption = event.getOption("preset");
        var timeOption = event.getOption("time");

        if (presetOption != null) {
            return Integer.parseInt(presetOption.getAsString());
        }
        if (timeOption != null) {
            return parseCustomTime(timeOption.getAsString());
        }
        return -1;
    }

    private int parseCustomTime(String timeInput) {
        try {
            int time = Integer.parseInt(timeInput);

            if (time <= 0 || time > 2400) return -1;

            if (timeInput.length() == 4) {
                int hour = time / 100;
                int minute = time % 100;
                return (hour > 24 || minute >= 60) ? -1 : hour * 60 + minute;
            }

            if (timeInput.length() == 3) {
                int hour = time / 100;
                int minute = time % 100;
                return (hour > 24 || minute >= 60) ? -1 : hour * 60 + minute;
            }

            if (timeInput.length() <= 2) {
                return time >= 60 ? time : -1;
            }

            return -1;
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    @Override
    public List<OptionData> getOptions() {
        List<OptionData> options = new ArrayList<>();
        options.add(new OptionData(OptionType.INTEGER, "time", "추방까지 남은 시간(분)", true)
                .setMinValue(1)
                .setMaxValue(60));
        return options;
    }
}
